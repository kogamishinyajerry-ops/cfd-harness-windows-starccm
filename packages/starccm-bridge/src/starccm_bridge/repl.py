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
        """Path to starccm+.bat, derived from the Codebuddy status check.

        Returns None if the install can't be found in the standard
        location (``C:\\Program Files\\Siemens\\...``).
        """
        candidates = list(Path(r"C:\Program Files\Siemens").rglob("starccm+.bat"))
        if not candidates:
            return None
        # Prefer the most-recently-modified install (in case multiple
        # STAR-CCM+ versions are installed).
        return max(candidates, key=lambda p: p.stat().st_mtime)

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
