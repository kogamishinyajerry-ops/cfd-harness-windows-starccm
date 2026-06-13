"""
build_r37_from_cst.py -- Thin CLI wrapper over cfd_harness.surrogate.builder.

The real implementation lives in
``src/cfd_harness/surrogate/builder.py`` (solver-agnostic, importable, unit-tested).
This script exists for backward-compatible CLI usage.

Usage:
  python scripts/build_r37_from_cst.py
  python scripts/build_r37_from_cst.py --cst-yaml knowledge/gold_standards/rotor37_cst_baseline.yaml
  python scripts/build_r37_from_cst.py --cst-coeffs 0.1,0.1,0.15,0.15,0.15,0.05,0.2,0.3,0.3,0.3,0.3,0.05
  python scripts/build_r37_from_cst.py --out stl_samples/sample_001.stl
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings

import numpy as np

# Allow running as a script from repo root.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

warnings.filterwarnings("ignore")

from cfd_harness.surrogate.builder import (
    EXTRUDE_M,
    HUB_RADIUS_M,
    N_OUTLINE_POINTS,
    CHORD_M_DEFAULT,
    build_watertight_stl,
    export_stl,
    load_cst_coefficients,
    outline_to_ccw,        # back-compat: re-exported for tests that still
                           # `from build_r37_from_cst import outline_to_ccw`
    verify_watertight,
)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--cst-yaml", default=None,
                        help="YAML file with 12-coeff vector under reference_values[0].value")
    parser.add_argument("--cst-coeffs", default=None,
                        help="12 comma-separated floats: A1..A6 lower, A7..A12 upper")
    parser.add_argument("--out", default="stl_samples/r37_baseline.stl",
                        help="Output STL path")
    parser.add_argument("--chord", type=float, default=CHORD_M_DEFAULT,
                        help=f"Chord length in m (default {CHORD_M_DEFAULT*1000:.1f} mm = R37 hub)")
    parser.add_argument("--extrude", type=float, default=EXTRUDE_M,
                        help=f"Axial extrude depth in m (default {EXTRUDE_M*1000:.0f} mm)")
    parser.add_argument("--hub-radius", type=float, default=HUB_RADIUS_M,
                        help=f"Hub radius in m (default {HUB_RADIUS_M*1000:.2f} mm)")
    args = parser.parse_args()

    coeffs = load_cst_coefficients(args.cst_yaml, args.cst_coeffs)
    assert coeffs.shape == (12,), f"expected 12 coeffs, got {coeffs.shape}"

    mesh = build_watertight_stl(
        coeffs,
        n_outline=N_OUTLINE_POINTS,
        extrude_m=args.extrude,
        hub_radius_m=args.hub_radius,
        chord_m=args.chord,
    )
    info = verify_watertight(mesh, label="r37_cst")
    for k, v in info.items():
        print(f"  {k}: {v}")

    nbytes = export_stl(mesh, args.out)
    print(f"\nSaved: {args.out} ({nbytes} bytes)")
    if not info["is_watertight"]:
        print("WARNING: mesh is NOT watertight. See info dict above.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
