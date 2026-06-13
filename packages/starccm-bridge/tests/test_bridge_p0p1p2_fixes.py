"""Unit tests for the P0 + P1.3 + P2.5 bridge fixes (commit dbde0b3 + P0-P2 series).

These tests are PURE unit tests — they do NOT require a STAR-CCM+
install, do NOT subprocess anything, and run in <1 second.  They
verify the in-process logic of:

  - ``_classify_spawn_error`` (P2.5 — error code mapping)
  - ``_STDERR_HEAD_CHARS`` (P2.5 — bumped from 500 → 4000)
  - ``CodebuddyRepl.export_scene`` (P1.3 — new method wired up)
  - ``CodebuddyRepl.run_macro(..., force_new=True)`` (P0.2 — adds -new)
  - ``CodebuddyRepl.starccm_bat`` (P0.1 — uses active version from
    ``use-version`` rather than the most-recently-modified heuristic)

Why these matter
----------------
The Stage 3+ pipeline cannot be exercised end-to-end without
STAR-CCM+ installed (real-solver tests are ``@pytest.mark.real_solver``).
But we can prove the *in-process* logic that sits between the
executor and the spawn — and that's where the P0 + P1.3 + P2.5
fixes live.  If any of these regress, the executor picks up
silent misbehavior (wrong STAR-CCM+ version, no -new flag, no
error code, etc.) that's hard to debug downstream.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from starccm_bridge.repl import (
    _STDERR_HEAD_CHARS,
    _classify_spawn_error,
    CodebuddyRepl,
    CodebuddyResponse,
)


# ---------- P2.5: error classification ----------

class TestClassifySpawnError:
    """`_classify_spawn_error` maps a spawn failure to a stable code."""

    def test_ok_when_returncode_zero(self):
        assert _classify_spawn_error("", "", 0) == "OK"

    def test_sim_lock_when_cannot_open_file(self):
        stderr = "Error: Cannot open file: foo.sim (specify -new to create)"
        assert _classify_spawn_error(stderr, "", 1) == "SIM_LOCK"

    def test_sim_lock_when_specify_new(self):
        stderr = "...specify -new to create the file"
        assert _classify_spawn_error(stderr, "", 1) == "SIM_LOCK"

    def test_sim_lock_detected_via_stdout(self):
        # Some versions of STAR-CCM+ print the error to stdout
        stdout = "Cannot open file: /path/to/old.sim"
        assert _classify_spawn_error("", stdout, 1) == "SIM_LOCK"

    def test_version_mismatch(self):
        stderr = "ERROR: Version mismatch between macro (R8) and solver (R6)"
        assert _classify_spawn_error(stderr, "", 1) == "VERSION_MISMATCH"

    def test_version_mismatch_requires_version_word_with_incompatible(self):
        # Guards the parenthesized precedence of the VERSION_MISMATCH rule:
        #   'version mismatch' OR ('incompatible' AND 'version').
        # A bare 'incompatible' (no 'version') must NOT classify as
        # VERSION_MISMATCH; 'incompatible ... version' must.
        assert _classify_spawn_error("file is incompatible", "", 1) != "VERSION_MISMATCH"
        assert _classify_spawn_error("incompatible solver version", "", 1) == "VERSION_MISMATCH"

    def test_macro_compile_error_with_symbol(self):
        stderr = "Foo.java:42: error: cannot find symbol\n  location: class Bar"
        assert _classify_spawn_error(stderr, "", 1) == "MACRO_COMPILE_ERROR"

    def test_macro_compile_error_via_java_path(self):
        stderr = "LidDrivenCavity.java:120: error: <identifier expected>"
        assert _classify_spawn_error(stderr, "", 1) == "MACRO_COMPILE_ERROR"

    def test_timeout(self):
        # returncode -1 + empty stdout = we hit the subprocess timeout
        assert _classify_spawn_error("TimeoutExpired", "", -1) == "TIMEOUT"

    def test_generic_spawn_fail_fallback(self):
        # No matching keyword — return SPAWN_FAIL rather than guess
        stderr = "Some unexpected error: see log"
        assert _classify_spawn_error(stderr, "", 99) == "SPAWN_FAIL"

    def test_does_not_overclassify(self):
        # Plain stderr with "error" word but no compile diagnostic
        # → NOT macro compile error.
        stderr = "JVM warning: ignoring option PermSize=32m"
        code = _classify_spawn_error(stderr, "", 1)
        assert code == "SPAWN_FAIL", f"got {code!r}, expected SPAWN_FAIL"


def test_stderr_truncation_bumped():
    """P2.5: stderr head for error messages is now 4000 chars (was 500)."""
    assert _STDERR_HEAD_CHARS >= 4000, (
        f"got {_STDERR_HEAD_CHARS}; expected >= 4000 so the full "
        f"javac diagnostic fits in the error message"
    )


# ---------- P1.3: export_scene method wired up ----------

class TestExportScene:
    """`CodebuddyRepl.export_scene` invokes the export-scene subcommand."""

    def test_method_exists(self):
        assert hasattr(CodebuddyRepl, "export_scene")
        assert callable(CodebuddyRepl.export_scene)

    def test_export_scene_builds_correct_argv(self, tmp_path):
        """export-scene <sim> --out <png> --field <f> --auto-range --lut <l>"""
        # Stub out _invoke to capture the argv
        captured: dict = {}

        def fake_invoke(cmd, args, timeout_s=None):
            captured["cmd"] = cmd
            captured["args"] = list(args)
            captured["timeout_s"] = timeout_s
            return CodebuddyResponse(
                ok=True, command=cmd, timestamp="", version="",
                data={"image_exists": True}, error=None,
            )

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl._invoke = fake_invoke
        out_png = str(tmp_path / "scene.png")
        resp = repl.export_scene(
            sim_path=r"D:\some\sim.sim",
            out_png=out_png,
            field="Velocity.Magnitude",
            auto_range=True,
            lut="spectrum",
            timeout_s=180,
        )
        assert resp.ok
        assert captured["cmd"] == "export-scene"
        assert captured["args"][0] == r"D:\some\sim.sim"
        assert "--out" in captured["args"]
        assert out_png in captured["args"]
        assert "--field" in captured["args"]
        assert "Velocity.Magnitude" in captured["args"]
        assert "--auto-range" in captured["args"]
        assert "--lut" in captured["args"]
        assert "spectrum" in captured["args"]
        assert captured["timeout_s"] == 180

    def test_export_scene_minimal_invocation(self):
        """Defaults: no out_png, no field, auto_range=True, lut='blue-red'."""
        captured: dict = {}

        def fake_invoke(cmd, args, timeout_s=None):
            captured["args"] = list(args)
            return CodebuddyResponse(
                ok=True, command=cmd, timestamp="", version="",
                data={"image_exists": False}, error=None,
            )

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl._invoke = fake_invoke
        repl.export_scene(sim_path=r"D:\foo\sim.sim")
        # Default: sim path only, then --auto-range (default True) +
        # --lut blue-red (default).  No --field / --out when caller
        # leaves them at their defaults.
        assert captured["args"] == [
            r"D:\foo\sim.sim", "--auto-range", "--lut", "blue-red",
        ]


# ---------- P0.2: run_macro force_new flag ----------

class TestRunMacroForceNew:
    """`run_macro(force_new=True)` must inject -new into the cmd argv."""

    def test_force_new_injects_dash_new(self, tmp_path):
        """When force_new=True, the spawned cmd must include '-new'."""
        # We can't actually run subprocess, but we can intercept the
        # cmd list right before subprocess.run via patching
        # ``subprocess.run`` itself.
        captured: dict = {}

        class FakeCompleted:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            return FakeCompleted()

        # StarCCM+ bat must exist for run_macro to proceed past the
        # "bat not found" guard.  Patch it.
        fake_bat = tmp_path / "starccm+.bat"
        fake_bat.write_text("@echo off\n", encoding="ascii")

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl.codebuddy_path = Path(tmp_path)
        repl.cli_script = Path(tmp_path) / "starccm_cli.py"
        repl.python_executable = sys.executable
        repl.default_timeout_s = 30
        # starccm_bat is a @property — we cannot set it directly.
        # Instead, inject the active-bat cache so the property
        # returns our fake_bat without subprocess.run.
        repl._active_bat_cache = fake_bat

        with patch("starccm_bridge.repl.subprocess.run", side_effect=fake_run):
            resp = repl.run_macro(
                sim_path=r"D:\s\sim.sim",
                macro_path=r"D:\m\macro.java",
                force_new=True,
                timeout_s=10,
            )

        assert resp.ok, f"run_macro failed: {resp.error!r}"
        # force_new=True must produce: <bat> <sim> -new -batch <macro>
        cmd = captured["cmd"]
        assert "-new" in cmd, f"'-new' missing from cmd: {cmd}"
        # Position: must come after <sim>, before -batch
        assert cmd.index("-new") > cmd.index(str(fake_bat))
        assert cmd.index("-new") < cmd.index("-batch")

    def test_force_new_default_omits_dash_new(self, tmp_path):
        """When force_new=False (default), the cmd must NOT include '-new'."""
        captured: dict = {}

        class FakeCompleted:
            returncode = 0
            stdout = "ok"
            stderr = ""

        def fake_run(cmd, **kwargs):
            captured["cmd"] = list(cmd)
            return FakeCompleted()

        fake_bat = tmp_path / "starccm+.bat"
        fake_bat.write_text("@echo off\n", encoding="ascii")

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl.codebuddy_path = Path(tmp_path)
        repl.cli_script = Path(tmp_path) / "starccm_cli.py"
        repl.python_executable = sys.executable
        repl.default_timeout_s = 30
        # Inject active-bat cache so starccm_bat property returns fake_bat
        repl._active_bat_cache = fake_bat

        with patch("starccm_bridge.repl.subprocess.run", side_effect=fake_run):
            resp = repl.run_macro(
                sim_path=r"D:\s\sim.sim",
                macro_path=r"D:\m\macro.java",
                timeout_s=10,
            )

        assert resp.ok
        assert "-new" not in captured["cmd"], (
            f"'-new' should NOT appear when force_new=False: {captured['cmd']}"
        )


# ---------- P0.1: starccm_bat prefers active version ----------

class TestStarccmBatResolvesActive:
    """P0.1: bridge.starccm_bat uses Codebuddy use-version, not heuristic."""

    def test_active_bat_returned_when_query_succeeds(self, tmp_path):
        """If use-version returns a valid path, that path is returned."""
        # Set up a fake starccm+.bat
        active_bat = tmp_path / "active_starccm+.bat"
        active_bat.write_text("@echo off\n", encoding="ascii")

        # Stub the use-version subprocess
        class FakeCompleted:
            returncode = 0
            stdout = '{"ok": true, "data": {"active_version": {"path": "' + str(active_bat).replace("\\", "\\\\") + '"}}}'
            stderr = ""

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl.codebuddy_path = Path(tmp_path)
        repl.cli_script = Path(tmp_path) / "starccm_cli.py"
        repl.python_executable = sys.executable
        repl.default_timeout_s = 30

        with patch("starccm_bridge.repl.subprocess.run", return_value=FakeCompleted()):
            bat = repl.starccm_bat
        assert bat is not None
        assert Path(bat).resolve() == active_bat.resolve()
        # Must be cached on the instance for subsequent calls
        assert repl._active_bat_cache is not None

    def test_fallback_to_heuristic_when_query_fails(self, tmp_path):
        """If use-version subprocess fails, fall back to the
        most-recently-modified heuristic.  This preserves the
        Stage 2+ behavior when Codebuddy is misconfigured.
        """
        # Plant a starccm+.bat under a path the heuristic would
        # find.  We can't easily fake C:\\Program Files\\Siemens
        # in a sandbox, so we just verify the fallback path is
        # taken (caching returns None) without raising.
        class FakeCompleted:
            returncode = 1
            stdout = ""
            stderr = "use-version failed"

        repl = CodebuddyRepl.__new__(CodebuddyRepl)
        repl.codebuddy_path = Path(tmp_path)
        repl.cli_script = Path(tmp_path) / "starccm_cli.py"
        repl.python_executable = sys.executable
        repl.default_timeout_s = 30

        with patch("starccm_bridge.repl.subprocess.run", return_value=FakeCompleted()):
            # We don't assert on the return value (depends on host
            # file system); we just assert no exception is raised
            # AND the cache is populated to None (so subsequent
            # calls go straight to the heuristic).
            _ = repl.starccm_bat
            assert repl._active_bat_cache is None
