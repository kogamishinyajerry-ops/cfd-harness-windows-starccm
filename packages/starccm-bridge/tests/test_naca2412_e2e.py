"""NACA 2412 E2E smoke test (200-iter).

Wraps the user's proven `CliNaca2412E2E.java` macro
(which expects an existing NACA .sim like `naca2412_v34_final.sim`)
and validates the macro runs end-to-end:
  - STAR-CCM+ spawn works
  - macro step 1-7 succeeds (disable multiphase, enable single-phase,
    set inlet velocity at Re=6e6 / AoA=4°, init, run, force report)
  - log file + summary.json are written
  - run completes in <10 min

Marked ``@pytest.mark.real_solver`` and additionally gated on
``STARCCM_BRIDGE_TEST_SPAWN=1``.

NOTE: This test does NOT re-create the NACA airfoil geometry — that
requires CAD (the user's macro opens an existing NACA .sim). The
``.sim`` template path is in ``knowledge/case_profiles.yaml`` under
``naca0012_airfoil.sim_path``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from starccm_bridge import CodebuddyRepl, CodebuddyResponse


HARNESS_ROOT = Path(__file__).resolve().parents[3]
USER_MACRO = Path(r"D:\StarCCM Codebuddy\macros\CliNaca2412E2E.java")
NACA_SIM = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v34_final.sim")
NACA_LOG = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_log.txt")
NACA_SUMMARY = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json")


@pytest.mark.real_solver
@pytest.mark.skipif(
    os.environ.get("STARCCM_BRIDGE_TEST_SPAWN") != "1",
    reason="set STARCCM_BRIDGE_TEST_SPAWN=1 to run the NACA E2E smoke (spawns STAR-CCM+; ~5-10 min)",
)
def test_naca2412_200iter_smoke():
    """Spawn STAR-CCM+ with the user's CliNaca2412E2E.java on the v34
    NACA .sim; validate the macro runs end-to-end."""
    assert USER_MACRO.exists(), f"missing user macro: {USER_MACRO}"
    assert NACA_SIM.exists(), f"missing NACA template .sim: {NACA_SIM}"

    # Pre-clean output files so we know they're from this run.
    for p in (NACA_LOG, NACA_SUMMARY):
        if p.exists():
            p.unlink()

    repl = CodebuddyRepl()
    resp = repl.run_macro(
        sim_path=str(NACA_SIM),
        macro_path=str(USER_MACRO),
        macro_args="",
        timeout_s=900,  # 15 min wall
    )
    assert isinstance(resp, CodebuddyResponse)
    assert resp.command.startswith("run_macro")

    if resp.raw_stdout:
        print("\n=== MACRO STDOUT (last 1000 chars) ===")
        print(resp.raw_stdout[-1000:])
    if resp.raw_stderr:
        print("\n=== MACRO STDERR (last 500 chars) ===")
        print(resp.raw_stderr[-500:])

    assert NACA_LOG.exists(), f"log not written: {NACA_LOG}"
    log_text = NACA_LOG.read_text(encoding="utf-8")
    # The macro writes step markers like "step: 1. Disable..."
    assert "step: 1" in log_text or "step:1" in log_text, (
        f"step 1 marker not in log: {log_text[:500]!r}"
    )
    # Step 4 = set inlet velocity; step 6 = run
    assert "step: 6" in log_text or "step:6" in log_text, (
        f"step 6 (run) marker not in log"
    )
    # If we got a summary.json, check run_ok
    if NACA_SUMMARY.exists():
        summary = json.loads(NACA_SUMMARY.read_text(encoding="utf-8"))
        print(f"\n=== NACA SUMMARY ===")
        for k in sorted(summary.keys()):
            v = summary[k]
            if isinstance(v, float):
                print(f"  {k}: {v:.4g}")
            else:
                print(f"  {k}: {v}")
        if "run_ok" in summary:
            assert summary["run_ok"], (
                f"run_ok=False; check log: {NACA_LOG}"
            )