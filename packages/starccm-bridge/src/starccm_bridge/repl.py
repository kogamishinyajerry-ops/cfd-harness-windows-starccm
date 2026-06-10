"""CodebuddyRepl: subprocess wrapper for the user's Codebuddy CLI.

Plane: ADAPTER_STARCCM (separate sub-package to keep
``cfd_harness.starccm_adapter`` importable on a fresh venv without
the bridge).

Stage 3+ implementation: this class actually subprocesses
``D:\\StarCCM Codebuddy\\starccm_cli.py <command> [args] --json`` and
parses the JSON response. The command is one of the 7 unified
commands from Codebuddy CLI v3+ (analyze / explore / modify / run /
pipeline / status / config) plus the 5 subcommands (inspect-sim /
vortex-street / launch-gui / use-version / export-*).

This module does NOT subclass Python's ``code.InteractiveConsole`` —
the CLI's REPL is interactive (TTY), but we drive it through one-shot
subprocess calls so the bridge can be embedded in any agent (or
pytest) without needing a TTY.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "CodebuddyRepl",
    "CodebuddyResponse",
    "CodebuddyError",
]


class CodebuddyError(RuntimeError):
    """Raised when the Codebuddy CLI returns ok=False (a structured error).

    The underlying JSON is preserved as ``self.response``.
    """
    def __init__(self, message: str, response: "CodebuddyResponse") -> None:
        super().__init__(message)
        self.response = response


class CodebuddyResponse:
    """A response from a single Codebuddy CLI invocation.

    The CLI's JSON schema (uniform across all 7+ commands):

    .. code-block:: json

        {
          "ok": true,
          "command": "vortex-street",
          "timestamp": "2026-06-09 23:31:12",
          "version": "15.0.0",
          "data": { /* command-specific */ },
          "error": null
        }

    When ``ok=False``, ``data`` may carry a diagnostic payload
    (eg. ``data.all_ok``) and ``error`` is set to a string (or null).
    """
    def __init__(
        self,
        ok: bool,
        command: str,
        timestamp: str,
        version: str,
        data: Dict[str, Any],
        error: Optional[str],
        *,
        returncode: int = 0,
        elapsed_s: float = 0.0,
        raw_stdout: str = "",
        raw_stderr: str = "",
    ) -> None:
        self.ok = ok
        self.command = command
        self.timestamp = timestamp
        self.version = version
        self.data = data
        self.error = error
        self.returncode = returncode
        self.elapsed_s = elapsed_s
        self.raw_stdout = raw_stdout
        self.raw_stderr = raw_stderr

    @property
    def is_structured_error(self) -> bool:
        """True iff the CLI returned ok=False (handled error)."""
        return not self.ok

    def __repr__(self) -> str:  # pragma: no cover (debug)
        return (
            f"CodebuddyResponse(ok={self.ok}, command={self.command!r}, "
            f"version={self.version!r}, elapsed={self.elapsed_s:.2f}s, "
            f"error={self.error!r})"
        )


# Environment for any spawn that touches STAR-CCM+'s embedded javac.
# Windows Chinese systems default to GBK, which silently corrupts .java
# macros with CJK characters. Set UTF-8 explicitly.
_SPAWN_ENV_OVERRIDES = {
    "JAVA_TOOL_OPTIONS": "-Dfile.encoding=UTF-8",
    "JAVAC_OPTIONS": "-encoding UTF-8",
}


# stderr truncation length for error messages.  STAR-CCM+ embeds
# javac diagnostics that can run 1-3 KB; 500 was too tight to see
# the actual compile / spawn error.  Bump to 4000 to capture the
# most useful prefix.
_STDERR_HEAD_CHARS = 4000


def _classify_spawn_error(stderr: str, stdout: str, returncode: int) -> str:
    """Classify a STAR-CCM+ spawn failure into a machine-readable code.

    Codes (stable contract — downstream code may switch on these):
      - ``"OK"``          — returncode == 0
      - ``"SIM_LOCK"``    — ``Cannot open file`` / ``specify -new`` —
        the prior .sim is locked / missing / version-mismatched.
        Caller should retry with ``force_new=True`` or after killing
        a stray GUI session.
      - ``"VERSION_MISMATCH"`` — ``version`` / ``build`` mismatch
        between the macro and the active STAR-CCM+ install.
      - ``"MACRO_COMPILE_ERROR"`` — javac-style diagnostics in
        stderr (eg. ``error:``, ``symbol:``).
      - ``"TIMEOUT"``     — returncode == -1 + empty stdout.
      - ``"SPAWN_FAIL"``  — generic catch-all.

    The classification is heuristic (substring match against
    stderr + stdout).  We intentionally keep it conservative — when
    in doubt, return ``"SPAWN_FAIL"`` rather than over-fitting.
    """
    if returncode == 0:
        return "OK"
    blob = (stderr or "") + "\n" + (stdout or "")
    blob_low = blob.lower()
    if "cannot open file" in blob_low or "specify -new" in blob_low:
        return "SIM_LOCK"
    if "version mismatch" in blob_low or "incompatible" in blob_low and "version" in blob_low:
        return "VERSION_MISMATCH"
    if "error:" in blob_low and ("symbol" in blob_low or "location:" in blob_low or ".java:" in blob_low):
        return "MACRO_COMPILE_ERROR"
    if returncode == -1 and not (stdout or "").strip():
        return "TIMEOUT"
    return "SPAWN_FAIL"


def _make_env() -> Dict[str, str]:
    env = os.environ.copy()
    env.update(_SPAWN_ENV_OVERRIDES)
    return env


def _try_parse_json(text: str) -> Optional[Dict[str, Any]]:
    """Try to parse a JSON object from text. Return None on failure."""
    if not text:
        return None
    # The CLI may emit non-JSON preamble (banners, INFO lines) before
    # the JSON payload. Find the first ``{`` and the matching ``}``.
    start = text.find("{")
    if start < 0:
        return None
    # Walk the braces to find the matching end.
    depth = 0
    in_string = False
    escape = False
    end = -1
    for i, ch in enumerate(text[start:], start=start):
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end < 0:
        return None
    snippet = text[start:end + 1]
    try:
        parsed = json.loads(snippet)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


class CodebuddyRepl:
    """Subprocess wrapper for the user's Codebuddy CLI.

    Parameters
    ----------
    codebuddy_path : str
        Absolute path to the Codebuddy repo root
        (default: ``D:\\StarCCM Codebuddy``).
    python_executable : str
        Python interpreter to use. Default: ``sys.executable``
        (whatever the harness was launched with).
    default_timeout_s : int
        Default per-call timeout. Some commands (eg. spawn-based
        ``run`` / ``vortex-street``) take 10-30s; complex DOE
        runs can take minutes. Override per-call via
        ``send_command(..., timeout_s=...)``.
    """
    DEFAULT_CODEBUDDY_PATH = r"D:\StarCCM Codebuddy"

    def __init__(
        self,
        codebuddy_path: str = DEFAULT_CODEBUDDY_PATH,
        python_executable: Optional[str] = None,
        default_timeout_s: int = 300,
    ) -> None:
        self.codebuddy_path = Path(codebuddy_path)
        self.cli_script = self.codebuddy_path / "starccm_cli.py"
        if not self.cli_script.exists():
            raise FileNotFoundError(
                f"Codebuddy CLI not found at {self.cli_script}. "
                f"Set codebuddy_path to the root of your Codebuddy repo."
            )
        self.python_executable = python_executable or _default_python()
        self.default_timeout_s = default_timeout_s

    @property
    def starccm_bat(self) -> Optional[Path]:
        """Path to starccm+.bat.

        Resolution order:
          1. Codebuddy ``use-version --json`` (the user-controlled
             active version — most reliable when multiple STAR-CCM+
             installs coexist)
          2. Fallback: rglob the standard install root, prefer
             most-recently-modified (legacy heuristic)

        Returns None if no install can be found.
        """
        # 1. Try the active-version query (cached on the instance).
        if not hasattr(self, "_active_bat_cache"):
            self._active_bat_cache = self._query_active_bat()
        if self._active_bat_cache is not None:
            return self._active_bat_cache
        # 2. Fallback heuristic
        candidates = list(Path(r"C:\Program Files\Siemens").rglob("starccm+.bat"))
        if not candidates:
            return None
        return max(candidates, key=lambda p: p.stat().st_mtime)

    def _query_active_bat(self) -> Optional[Path]:
        """Subprocess ``python starccm_cli.py use-version --json`` and
        return the active ``starccm+.bat`` Path.  None on any failure.
        """
        try:
            proc = subprocess.run(
                [self.python_executable, str(self.cli_script),
                 "use-version", "--json"],
                cwd=str(self.codebuddy_path),
                capture_output=True, text=True, timeout=15, check=False,
            )
        except (subprocess.TimeoutExpired, OSError):
            return None
        if proc.returncode != 0:
            return None
        payload = _try_parse_json(proc.stdout)
        if not payload:
            return None
        active = payload.get("active_version") or payload.get("data", {}).get("active_version")
        if not isinstance(active, dict):
            return None
        path_str = active.get("path")
        if not path_str:
            return None
        p = Path(path_str)
        return p if p.exists() else None

    # ----- low-level: subprocess invocation -----
    def _invoke(
        self,
        command: str,
        args: Sequence[str],
        timeout_s: Optional[int] = None,
    ) -> CodebuddyResponse:
        """Invoke ``python starccm_cli.py <command> <args...> --json``.

        Returns a ``CodebuddyResponse``. Raises ``CodebuddyError`` if
        the CLI returns ``ok=False`` AND the user passed
        ``raise_on_error=True`` (default for most call sites).
        """
        cmd: List[str] = [
            self.python_executable,
            str(self.cli_script),
            command,
            *args,
            "--json",
        ]
        timeout = timeout_s if timeout_s is not None else self.default_timeout_s
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.codebuddy_path),
                env=_make_env(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            elapsed = time.monotonic() - t0
            raise CodebuddyError(
                f"Codebuddy CLI timed out after {timeout}s: "
                f"command={command!r} args={list(args)!r}",
                response=CodebuddyResponse(
                    ok=False,
                    command=command,
                    timestamp="",
                    version="",
                    data={},
                    error=f"timeout after {timeout}s",
                    returncode=-1,
                    elapsed_s=elapsed,
                    raw_stdout=e.stdout or "",
                    raw_stderr=e.stderr or "",
                ),
            ) from e
        elapsed = time.monotonic() - t0
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        parsed = _try_parse_json(stdout)
        if parsed is None:
            # CLI didn't return JSON (eg. threw an unhandled exception,
            # printed to stderr, or the timeout was too short for the
            # JSON header to flush). Surface as a structured error.
            return CodebuddyResponse(
                ok=False,
                command=command,
                timestamp="",
                version="",
                data={},
                error=(
                    f"non-JSON output (returncode={proc.returncode}); "
                    f"stderr={stderr.strip()[:500]!r}; "
                    f"stdout_head={stdout[:200]!r}"
                ),
                returncode=proc.returncode,
                elapsed_s=elapsed,
                raw_stdout=stdout,
                raw_stderr=stderr,
            )
        return CodebuddyResponse(
            ok=bool(parsed.get("ok", False)),
            command=str(parsed.get("command", command)),
            timestamp=str(parsed.get("timestamp", "")),
            version=str(parsed.get("version", "")),
            data=parsed.get("data") or {},
            error=parsed.get("error"),
            returncode=proc.returncode,
            elapsed_s=elapsed,
            raw_stdout=stdout,
            raw_stderr=stderr,
        )

    # ----- high-level: each Codebuddy command -----
    def status(self, timeout_s: Optional[int] = None) -> CodebuddyResponse:
        """``status`` — health check (install + GUI + license)."""
        return self._invoke("status", [], timeout_s=timeout_s)

    def config(self, timeout_s: Optional[int] = None) -> CodebuddyResponse:
        """``config`` — print the current Codebuddy config."""
        return self._invoke("config", [], timeout_s=timeout_s)

    def inspect_sim(self, sim_path: str, timeout_s: Optional[int] = None) -> CodebuddyResponse:
        """``inspect-sim <sim>`` — static parse of a .sim file (no spawn)."""
        return self._invoke("inspect-sim", [sim_path], timeout_s=timeout_s)

    def analyze(self, sim_path: str, timeout_s: Optional[int] = None) -> CodebuddyResponse:
        """``analyze <sim>`` — deep analysis (no spawn, but heavy on .sim)."""
        return self._invoke("analyze", [sim_path], timeout_s=timeout_s)

    def explore(self, sim_path: str, timeout_s: Optional[int] = None) -> CodebuddyResponse:
        """``explore <sim>`` — explore case structure (no spawn)."""
        return self._invoke("explore", [sim_path], timeout_s=timeout_s)

    def run(
        self,
        sim_path: str,
        iters: Optional[int] = None,
        timeout_s: Optional[int] = None,
    ) -> CodebuddyResponse:
        """``run <sim> [--iters N]`` — spawn STAR-CCM+ and run a solve.

        ``iters`` is the maximum iteration count passed to the solver.
        If None, the CLI's default is used (typically 500).
        """
        args: List[str] = [sim_path]
        if iters is not None:
            args.extend(["--iters", str(iters)])
        return self._invoke("run", args, timeout_s=timeout_s)

    def pipeline(
        self,
        sim_path: str,
        instructions: Sequence[str],
        timeout_s: Optional[int] = None,
    ) -> CodebuddyResponse:
        """``pipeline <sim> [指令...]`` — multi-step modify + run in one spawn."""
        return self._invoke("pipeline", [sim_path, *instructions], timeout_s=timeout_s)

    def vortex_street(
        self,
        sim_path: Optional[str] = None,
        macro: Optional[str] = None,
        out_dir: Optional[str] = None,
        timeout_s: Optional[int] = 600,
    ) -> CodebuddyResponse:
        """``vortex-street`` — proven E2E path for cylinder wake.

        ``sim_path`` defaults to ``Cases/cyl_flow_v9m.sim`` if None.
        ``macro`` defaults to ``macros/VortexStreet.java``.
        ``out_dir`` defaults to ``Cases/Results``.
        """
        args: List[str] = []
        if sim_path:
            args.append(sim_path)
        if macro:
            args.extend(["--macro", macro])
        if out_dir:
            args.extend(["--out-dir", out_dir])
        return self._invoke("vortex-street", args, timeout_s=timeout_s)

    def export_field(
        self,
        sim_path: str,
        field: str = "Velocity",
        out_csv: Optional[str] = None,
        timeout_s: Optional[int] = None,
    ) -> CodebuddyResponse:
        """``export-field <sim> [--field X] [--out path]`` — extract a field as CSV."""
        args: List[str] = [sim_path, "--field", field]
        if out_csv:
            args.extend(["--out", out_csv])
        return self._invoke("export-field", args, timeout_s=timeout_s)

    def export_scene(
        self,
        sim_path: str,
        out_png: Optional[str] = None,
        field: str = "",
        auto_range: bool = True,
        lut: str = "blue-red",
        timeout_s: int = 120,
    ) -> CodebuddyResponse:
        """``export-scene <sim>`` — render a Scene to PNG (v55+).

        This is the bridge to the Codebuddy ``export-scene`` subcommand
        which spawns a ``CliExportScene.java`` macro with the chosen
        field + LUT + range.  Use this AFTER a run-macro / vortex-street
        spawn finishes, to capture a hardcopy of the converged field.

        Parameters
        ----------
        sim_path : str
            The solved ``.sim`` file.
        out_png : str, optional
            Output PNG path.  Defaults to
            ``Cases/Results/<sim_name>_scene.png``.
        field : str
            Field function name to bind (eg. ``"Pressure"``,
            ``"Velocity.Magnitude"``).  Empty string reuses the
            first existing scene in the sim.
        auto_range : bool
            If True, compute the color range from the field data
            (default).  If False, use --range-min/--range-max
            (which the CLI hardcodes; the bridge does not expose
            manual ranges yet — extend if you need them).
        lut : str
            Lookup-table name.  Common choices: ``"blue-red"`` (default),
            ``"spectrum"``, ``"grayscale"``, ``"thermal"``, ``"cool-warm"``.
        """
        args: List[str] = [sim_path]
        if out_png:
            args.extend(["--out", out_png])
        if field:
            args.extend(["--field", field])
        if auto_range:
            args.append("--auto-range")
        if lut:
            args.extend(["--lut", lut])
        return self._invoke("export-scene", args, timeout_s=timeout_s)

    def run_macro(
        self,
        sim_path: str,
        macro_path: str,
        macro_args: str = "",
        timeout_s: int = 1800,
        env: Optional[Dict[str, str]] = None,
        force_new: bool = False,
    ) -> CodebuddyResponse:
        """Spawn STAR-CCM+ directamente con un Java macro (bypass CLI).

        This is the canonical Stage 3+ path for case-specific
        macros (eg. ``LidDrivenCavity.java``). The CLI's ``run``
        command is thin (just ``--iters``); arbitrary macros need
        the direct ``[bat, sim, -batch, macro]`` spawn pattern.

        Parameters
        ----------
        sim_path : str
            Path to a (possibly empty) .sim file. STAR-CCM+ will
            open / create this file before running the macro.
        macro_path : str
            Absolute path to the Java macro file.
        macro_args : str
            Optional space-joined arg string passed to the
            macro's ``getArgs()``. NOTE: STAR-CCM+ parses the
            trailing args as CLI flags unless the macro is
            invoked via -J-Dsystem.properties or env vars. Use
            the ``env=`` parameter for smoke-test overrides.
        timeout_s : int
            Per-spawn timeout. Default 30 min.
        env : dict, optional
            Extra environment variables to merge with the default
            STAR-CCM+ spawn env (which already includes
            ``JAVA_TOOL_OPTIONS=-Dfile.encoding=UTF-8`` and
            ``JAVAC_OPTIONS=-encoding UTF-8``).
        force_new : bool
            If True, pass ``-new`` to STAR-CCM+ so it creates a new
            ``.sim`` at ``sim_path`` (overwriting any existing one).
            Use this for from-scratch cases (LDC builds from STL)
            or when a prior sim is corrupted / version-mismatched.
        """
        starccm_bat = self.starccm_bat
        if starccm_bat is None or not starccm_bat.exists():
            return CodebuddyResponse(
                ok=False,
                command=f"run_macro({Path(macro_path).name})",
                timestamp="",
                version="",
                data={},
                error=f"starccm+.bat not found in C:\\Program Files\\Siemens",
                returncode=-1,
                elapsed_s=0.0,
            )
        cmd: List[str] = [str(starccm_bat), str(sim_path)]
        if force_new:
            cmd.append("-new")
        cmd.extend(["-batch", str(macro_path)])
        if macro_args:
            cmd.append(macro_args)
        spawn_env = _make_env()
        if env:
            spawn_env.update(env)
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.codebuddy_path),
                env=spawn_env,
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            elapsed = time.monotonic() - t0
            raise CodebuddyError(
                f"STAR-CCM+ spawn timed out after {timeout_s}s: macro={macro_path!r}",
                response=CodebuddyResponse(
                    ok=False,
                    command=f"run_macro({Path(macro_path).name})",
                    timestamp="",
                    version="",
                    data={},
                    error=f"timeout after {timeout_s}s",
                    returncode=-1,
                    elapsed_s=elapsed,
                    raw_stdout=e.stdout or "",
                    raw_stderr=e.stderr or "",
                ),
            ) from e
        elapsed = time.monotonic() - t0
        ok = proc.returncode == 0
        return CodebuddyResponse(
            ok=ok,
            command=f"run_macro({Path(macro_path).name})",
            timestamp="",
            version="",
            data={
                "sim_path": str(sim_path),
                "macro_path": str(macro_path),
                "starccm_bat": str(starccm_bat),
                "returncode": proc.returncode,
                "error_code": _classify_spawn_error(
                    proc.stderr or "", proc.stdout or "", proc.returncode
                ),
            },
            error=(
                None if ok
                else f"STAR-CCM+ returned RC={proc.returncode}; "
                     f"stderr_head={proc.stderr[:_STDERR_HEAD_CHARS]!r}"
            ),
            returncode=proc.returncode,
            elapsed_s=elapsed,
            raw_stdout=proc.stdout or "",
            raw_stderr=proc.stderr or "",
        )
        cmd: List[str] = [str(starccm_bat), str(sim_path), "-batch", str(macro_path)]
        if macro_args:
            cmd.append(macro_args)
        t0 = time.monotonic()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.codebuddy_path),
                env=_make_env(),
                capture_output=True,
                text=True,
                timeout=timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as e:
            elapsed = time.monotonic() - t0
            raise CodebuddyError(
                f"STAR-CCM+ spawn timed out after {timeout_s}s: macro={macro_path!r}",
                response=CodebuddyResponse(
                    ok=False,
                    command=f"run_macro({Path(macro_path).name})",
                    timestamp="",
                    version="",
                    data={},
                    error=f"timeout after {timeout_s}s",
                    returncode=-1,
                    elapsed_s=elapsed,
                    raw_stdout=e.stdout or "",
                    raw_stderr=e.stderr or "",
                ),
            ) from e
        elapsed = time.monotonic() - t0
        # The macro's stdout is just text (no JSON). We mark this
        # call as ok if STAR-CCM+ returned RC=0. The real verdict
        # is in the macro's ``<Results>/<case>_summary.json`` file,
        # which the executor picks up.
        ok = proc.returncode == 0
        return CodebuddyResponse(
            ok=ok,
            command=f"run_macro({Path(macro_path).name})",
            timestamp="",
            version="",
            data={
                "sim_path": str(sim_path),
                "macro_path": str(macro_path),
                "starccm_bat": str(starccm_bat),
                "returncode": proc.returncode,
                "error_code": _classify_spawn_error(
                    proc.stderr or "", proc.stdout or "", proc.returncode
                ),
            },
            error=(
                None if ok
                else f"STAR-CCM+ returned RC={proc.returncode}; "
                     f"stderr_head={proc.stderr[:_STDERR_HEAD_CHARS]!r}"
            ),
            returncode=proc.returncode,
            elapsed_s=elapsed,
            raw_stdout=proc.stdout or "",
            raw_stderr=proc.stderr or "",
        )

    # ----- raw escape hatch -----
    def send_command(
        self,
        command: str,
        args: Sequence[str] = (),
        timeout_s: Optional[int] = None,
    ) -> CodebuddyResponse:
        """Raw escape hatch: send any Codebuddy command + args.

        Use this for commands not wrapped by a dedicated method
        (eg. ``modify``, ``export-image``, ``export-report``).
        """
        return self._invoke(command, list(args), timeout_s=timeout_s)


def _default_python() -> str:
    """Pick the Python interpreter: PYTHON env var → sys.executable."""
    import sys
    return sys.executable
