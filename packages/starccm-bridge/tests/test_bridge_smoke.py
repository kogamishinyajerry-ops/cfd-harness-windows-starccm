"""Real-solver proof-of-concept tests for the Codebuddy REPL bridge.

These tests exercise the bridge against the user's actual
``D:\\StarCCM Codebuddy`` install. They are marked
``@pytest.mark.real_solver`` so the default ``pytest -m "not
real_solver"`` skips them — but ``pytest -m real_solver`` runs them
to prove the bridge works.

What this test does NOT do:
  - It does not require a STAR-CCM+ license to be active
    (status + inspect-sim are license-free).
  - It does not write to the .sim file (inspect-sim is read-only).
  - It does not run a solver iteration (those are slow + license-heavy).

What this test DOES do:
  - Verifies the bridge subprocess actually launches Codebuddy CLI.
  - Verifies the JSON schema is the expected ``{ok, command,
    timestamp, version, data, error}`` shape.
  - Verifies the status check finds the STAR-CCM+ install.
  - Verifies inspect-sim can read a real .sim file.
  - Optionally: spawns vortex-street against an existing solved
    cylinder sim (slow, ~11s+, requires license) — guarded by
    ``STARCCM_BRIDGE_TEST_SPAWN=1`` env var.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from starccm_bridge import CodebuddyRepl, CodebuddyResponse, CodebuddyError


CODEBUDDY_PATH = r"D:\StarCCM Codebuddy"


@pytest.fixture
def repl() -> CodebuddyRepl:
    """A CodebuddyRepl pointing at the user's actual Codebuddy install."""
    return CodebuddyRepl(codebuddy_path=CODEBUDDY_PATH, default_timeout_s=60)


@pytest.mark.real_solver
def test_repl_construction_succeeds(repl):
    """CodebuddyRepl can find the CLI script at the configured path."""
    assert repl.cli_script.exists()
    assert repl.cli_script.name == "starccm_cli.py"


@pytest.mark.real_solver
def test_repl_finds_starccm_install(repl):
    """The bridge can locate the STAR-CCM+ install (starccm+.bat)."""
    bat = repl.starccm_bat
    if bat is None:
        pytest.skip("STAR-CCM+ install not found in C:\\Program Files\\Siemens")
    assert bat.exists()
    assert bat.name == "starccm+.bat"


@pytest.mark.real_solver
def test_status_command_runs(repl):
    """``status`` returns a structured response (even if all_ok=False)."""
    resp = repl.status(timeout_s=30)
    assert isinstance(resp, CodebuddyResponse)
    assert resp.command == "status"
    # The CLI may return ok=false (if GUI is not running, etc.),
    # but it MUST return a JSON payload.
    assert resp.version != "", f"empty version; raw_stdout={resp.raw_stdout[:500]!r}"
    # The data block must include checks
    assert "checks" in resp.data or "all_ok" in resp.data, (
        f"unexpected data shape: {list(resp.data)[:10]}"
    )


@pytest.mark.real_solver
def test_inspect_sim_against_real_sim(repl):
    """``inspect-sim`` reads a real .sim file and returns the static parse."""
    sim_path = r"D:\StarCCM Codebuddy\Cases\cyl_vortex_v161R_v26_solved.sim"
    if not Path(sim_path).exists():
        pytest.skip(f"sim not found: {sim_path}")
    resp = repl.inspect_sim(sim_path, timeout_s=60)
    assert resp.command == "inspect-sim"
    # inspect-sim is a license-free static parse; it must succeed
    assert resp.ok, f"inspect-sim failed: error={resp.error!r}, raw={resp.raw_stdout[:500]!r}"
    # The data block must include the scan + classifications
    assert "scan" in resp.data
    assert "classifications" in resp.data
    # Cylinder sim has InletBoundary, OutletBoundary, WallBoundary etc.
    classifications = resp.data["classifications"]
    assert "geometry" in classifications


@pytest.mark.real_solver
@pytest.mark.skipif(
    os.environ.get("STARCCM_BRIDGE_TEST_SPAWN") != "1",
    reason="set STARCCM_BRIDGE_TEST_SPAWN=1 to run the vortex-street spawn (slow + license-heavy)",
)
def test_vortex_street_spawn_smoke(repl, tmp_path):
    """End-to-end smoke: spawn STAR-CCM+ via vortex-street on an existing solved sim.

    This is the proof-of-concept that the bridge + the executor
    wiring actually works against a real solver install. It
    typically takes ~11-30s and requires an active STAR-CCM+
    license.
    """
    sim_path = r"D:\StarCCM Codebuddy\Cases\cyl_vortex_v161R_v26_solved.sim"
    if not Path(sim_path).exists():
        pytest.skip(f"sim not found: {sim_path}")
    out_dir = tmp_path / "vortex_out"
    resp = repl.vortex_street(
        sim_path=sim_path,
        out_dir=str(out_dir),
        timeout_s=300,
    )
    # We don't assert ok=True (license-dependent), but we DO assert
    # the response is structured and the subprocess returned.
    assert isinstance(resp, CodebuddyResponse)
    assert resp.command == "vortex-street"
    # If the spawn succeeded, the output dir should have artifacts
    if resp.ok:
        assert out_dir.exists()
        # The vortex-street command writes a summary.json + .sim + log
        assert (out_dir / "summary.json").exists() or any(out_dir.glob("*.json"))
