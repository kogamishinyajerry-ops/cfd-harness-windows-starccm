"""
cst_lhs.py -- Thin CLI wrapper over cfd_harness.surrogate.lhs.

The real implementation lives in
``src/cfd_harness/surrogate/lhs.py`` (solver-agnostic, importable, unit-tested).
This script exists for backward-compatible CLI usage and for users who do
not run the harness as a package.

Usage:
  python scripts/cst_lhs.py
  python scripts/cst_lhs.py --n 100 --seed 42 --out-dir stl_samples/lhs
  python scripts/cst_lhs.py --n 1000 --seed 7
"""
from __future__ import annotations

import argparse
import os
import sys

import numpy as np

# Make cfd_harness importable when run as a bare script.
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from cfd_harness.surrogate.lhs import (
    DEFAULT_BASELINE_YAML,
    load_lhs_bounds,
    sample_lhs,
    write_lhs_outputs,
)

DEFAULT_YAML = os.path.join(_REPO_ROOT, DEFAULT_BASELINE_YAML)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--n", type=int, default=100, help="Number of LHS samples (default 100)")
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default 42)")
    parser.add_argument("--yaml", default=DEFAULT_YAML, help="Gold-standard YAML with lhs_bounds")
    parser.add_argument("--out-dir", default="stl_samples/lhs",
                        help="Output directory (default stl_samples/lhs)")
    args = parser.parse_args()

    lb, ub = load_lhs_bounds(args.yaml)
    samples = sample_lhs(args.n, lb, ub, seed=args.seed)
    assert samples.shape == (args.n, 12)
    assert np.all(samples >= lb - 1e-9), f"min {samples.min(0)} < lb {lb}"
    assert np.all(samples <= ub + 1e-9), f"max {samples.max(0)} > ub {ub}"

    sizes = write_lhs_outputs(samples, args.out_dir, args.seed, args.yaml, lb, ub)

    print(f"Generated {args.n} LHS samples in 12-dim CST design space.")
    print(f"Bounds (A1..A6 lower, A7..A12 upper):")
    print(f"  lb: {lb.tolist()}")
    print(f"  ub: {ub.tolist()}")
    print(f"Sample statistics:")
    print(f"  mean: {samples.mean(0).round(4).tolist()}")
    print(f"  std : {samples.std(0).round(4).tolist()}")
    print(f"Outputs:")
    for fn, sz in sizes.items():
        rel = os.path.relpath(fn, ".")
        print(f"  {rel} ({sz} bytes)")


if __name__ == "__main__":
    main()
