#!/usr/bin/env python
"""Smoke-test the CLI for all 16 cases (mock executor).

Used by the chief engineer to verify the v0.1.1 16-case coverage pass.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

CASES = [
    "lid_driven_cavity",
    "naca0012_airfoil",
    "circular_cylinder_wake",
    "backward_facing_step",
    "backward_facing_step_steady",
    "duct_flow",
    "fully_developed_plane_channel_flow",
    "plane_channel_flow",
    "axisymmetric_impinging_jet",
    "cylinder_crossflow",
    "impinging_jet",
    "turbulent_flat_plate",
    "differential_heated_cavity",
    "rayleigh_benard_convection",
    "cht_pipe_gnielinski",
    "cht_straight_fin",
]

OUT_ROOT = Path("reports_test/v1_16cases")


def main() -> int:
    if OUT_ROOT.exists():
        # Re-runnable: trash the previous run output
        import shutil
        shutil.rmtree(OUT_ROOT)
    pass_count = 0
    fail_count = 0
    fails: list[str] = []
    print(f"Smoke-running {len(CASES)} cases through cfd_harness.cli.run (mock executor)")
    print(f"output root: {OUT_ROOT}")
    print("-" * 60)
    for case in CASES:
        proc = subprocess.run(
            [sys.executable, "-m", "cfd_harness.cli.run",
             "--case", case, "--executor", "mock",
             "--output", str(OUT_ROOT)],
            capture_output=True,
            text=True,
        )
        if proc.returncode == 0:
            pass_count += 1
            print(f"  PASS  {case}")
        else:
            fail_count += 1
            fails.append(case)
            # Pull the last "verdict" / "executor" / "audit" line for context
            tail = (proc.stdout + proc.stderr).strip().splitlines()[-6:]
            print(f"  FAIL  {case}  (exit={proc.returncode})")
            for line in tail:
                print(f"        {line}")
    print("-" * 60)
    print(f"PASS: {pass_count} / {len(CASES)}   FAIL: {fail_count}")
    if fail_count:
        print(f"Failed cases: {', '.join(fails)}")
    return 0 if fail_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
