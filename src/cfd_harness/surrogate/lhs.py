"""
lhs.py -- Latin Hypercube Sampling of CST 12-coefficient design space.

For M3 surrogate training we sample N points in the 12-dim CST design space
[lower A1..A6 + upper A7..A12] with per-variable bounds read from a
gold-standard YAML (typically ``knowledge/gold_standards/rotor37_cst_baseline.yaml``).

Uses ``scipy.stats.qmc.LatinHypercube`` (centered-discrepancy optimization) --
better space-filling than naive random LHS. Solver-agnostic.

This module is the in-package implementation. The ``scripts/cst_lhs.py`` CLI
is a thin wrapper around it.
"""
from __future__ import annotations

import json
import os
from typing import Optional, Tuple

import numpy as np
import yaml
from scipy.stats import qmc

# Default yaml location (relative to repo root). Overridable via argument.
DEFAULT_BASELINE_YAML = os.path.join(
    "knowledge", "gold_standards", "rotor37_cst_baseline.yaml"
)

N_VARS = 12  # 6 lower + 6 upper Bernstein coefficients


def load_lhs_bounds(yaml_path: Optional[str] = None) -> Tuple[np.ndarray, np.ndarray]:
    """Load per-variable min/max bounds from a gold-standard YAML.

    The YAML must have a top-level ``lhs_bounds`` key with ``lower.min/max``
    and ``upper.min/max`` arrays of length 6 each.

    Args:
        yaml_path: optional override. If None (default), resolves the
            baseline YAML in this order:
              1. ``DEFAULT_BASELINE_YAML`` resolved against the current
                 working directory (the package root, when run via
                 ``python -m cfd_harness.surrogate.lhs``).
              2. ``knowledge/gold_standards/rotor37_cst_baseline.yaml``
                 resolved against ``scripts/`` (the repo-root layout used
                 by ``scripts/cst_lhs.py``).

    Returns:
        (lb, ub) each shape (12,) with order
        [A1..A6 lower, A7..A12 upper].
    """
    if yaml_path is None:
        candidates = [
            DEFAULT_BASELINE_YAML,                                     # cwd-relative
            os.path.join("scripts", DEFAULT_BASELINE_YAML),            # scripts/-relative
            os.path.join("..", "knowledge", "gold_standards",
                         "rotor37_cst_baseline.yaml"),                  # cst_lhs.py view
            os.path.join("..", "..", "knowledge", "gold_standards",
                         "rotor37_cst_baseline.yaml"),                  # tests/ view
        ]
        yaml_path = None
        for c in candidates:
            if os.path.exists(c):
                yaml_path = c
                break
        if yaml_path is None:
            raise FileNotFoundError(
                f"Could not find rotor37_cst_baseline.yaml in any of: {candidates}"
            )

    with open(yaml_path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    b = d["lhs_bounds"]
    lb = np.array(b["lower"]["min"] + b["upper"]["min"], dtype=np.float64)
    ub = np.array(b["lower"]["max"] + b["upper"]["max"], dtype=np.float64)
    assert lb.shape == (N_VARS,) and ub.shape == (N_VARS,), (
        f"expected 12-dim bounds, got lb={lb.shape} ub={ub.shape}"
    )
    assert np.all(lb < ub), f"lb must be < ub elementwise; got lb={lb}, ub={ub}"
    return lb, ub


def sample_lhs(n: int, lb: np.ndarray, ub: np.ndarray, seed: int = 42) -> np.ndarray:
    """Generate N LHS points in [lb, ub] (inclusive) box.

    Returns (N, 12) array of CST coefficient vectors in
    [A1..A6 lower, A7..A12 upper] order.
    """
    assert lb.shape == ub.shape == (N_VARS,), (
        f"expected 12-dim bounds, got lb={lb.shape} ub={ub.shape}"
    )
    sampler = qmc.LatinHypercube(d=N_VARS, seed=seed)
    unit = sampler.random(n=n)            # (N, 12) in [0, 1]^12
    samples = qmc.scale(unit, l_bounds=lb, u_bounds=ub)
    return samples


def write_lhs_outputs(samples: np.ndarray, out_dir: str,
                      seed: int, bounds_source: str,
                      lb: np.ndarray, ub: np.ndarray) -> dict:
    """Persist the LHS samples as .npy / .csv / .json and return file sizes.

    Files written under ``out_dir``:
      - lhs_samples.npy: (N, 12) array, dtype float64
      - lhs_samples.csv: same with header
      - lhs_samples.json: per-sample index + coeffs + bounds + seed

    Returns:
        dict mapping filename to absolute file size in bytes.
    """
    os.makedirs(out_dir, exist_ok=True)
    n = samples.shape[0]
    assert samples.shape == (n, N_VARS)

    npy_path = os.path.join(out_dir, "lhs_samples.npy")
    csv_path = os.path.join(out_dir, "lhs_samples.csv")
    json_path = os.path.join(out_dir, "lhs_samples.json")

    np.save(npy_path, samples)

    header = ",".join([f"A{i + 1}" for i in range(N_VARS)])
    np.savetxt(csv_path, samples, delimiter=",", header=header, comments="")

    samples_list = [
        {"index": int(i), "cst_coefficients": samples[i].tolist()}
        for i in range(n)
    ]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "method": "scipy.stats.qmc.LatinHypercube",
                "n_samples": n,
                "seed": seed,
                "bounds_source": bounds_source,
                "bounds": {
                    "lower_min": lb[:6].tolist(),
                    "lower_max": ub[:6].tolist(),
                    "upper_min": lb[6:].tolist(),
                    "upper_max": ub[6:].tolist(),
                },
                "samples": samples_list,
            },
            f,
            indent=2,
        )

    return {p: os.path.getsize(p) for p in (npy_path, csv_path, json_path)}


__all__ = [
    "N_VARS",
    "DEFAULT_BASELINE_YAML",
    "load_lhs_bounds",
    "sample_lhs",
    "write_lhs_outputs",
]
