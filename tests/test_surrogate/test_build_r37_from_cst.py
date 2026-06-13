"""
Tests for build_r37_from_cst.py (CST -> watertight STL pipeline).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

# Make sure we can import from cfd_harness and scripts
_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'scripts'))

from build_r37_from_cst import (
    load_cst_coefficients, outline_to_ccw, build_watertight_stl,
    verify_watertight, HUB_RADIUS_M, EXTRUDE_M,
)


# ---------- 1. Outline orientation ----------
def test_outline_to_ccw_already_ccw():
    # Build a square that's already CCW (positive shoelace)
    sq = np.array([[0, 0], [1, 0], [1, 1], [0, 1]], dtype=float)
    out = outline_to_ccw(sq)
    assert np.allclose(out, sq)


def test_outline_to_ccw_cw_flipped():
    # Square listed CW (negative shoelace)
    sq_cw = np.array([[0, 0], [0, 1], [1, 1], [1, 0]], dtype=float)
    out = outline_to_ccw(sq_cw)
    # Should be reversed
    assert np.allclose(out, sq_cw[::-1])


# ---------- 2. Watertight STL ----------
def test_build_baseline_is_watertight():
    from cfd_harness.surrogate.cst import DEFAULT_LOWER, DEFAULT_UPPER
    coeffs = np.concatenate([DEFAULT_LOWER, DEFAULT_UPPER])
    mesh = build_watertight_stl(coeffs)
    info = verify_watertight(mesh, label='baseline')
    assert info['is_watertight'], f"baseline mesh not watertight: {info}"
    assert info['is_winding_consistent']
    assert info['n_faces'] >= 4
    # Volume sanity: chord * thickness * extrude (approx)
    # 40.5mm chord, 12% thick, 20mm extrude -> 4.05e-2 * 4.86e-3 * 2e-2 ~ 3.9e-6
    # But our baseline is a 2D section extruded; volume should be on this order.
    assert 1e-7 < info['volume_m3'] < 1e-4, f"volume {info['volume_m3']} out of range"


def test_build_yaml_is_watertight():
    yaml_path = os.path.join(_REPO, 'knowledge', 'gold_standards',
                             'rotor37_cst_baseline.yaml')
    if not os.path.exists(yaml_path):
        pytest.skip("rotor37_cst_baseline.yaml not present")
    coeffs = load_cst_coefficients(yaml_path=yaml_path)
    assert coeffs.shape == (12,)
    mesh = build_watertight_stl(coeffs)
    info = verify_watertight(mesh, label='from_yaml')
    assert info['is_watertight']
    assert info['n_faces'] >= 4


def test_build_random_coeffs_robustness():
    """Test that a range of random CST coefficient vectors still produce watertight meshes."""
    from cfd_harness.surrogate.cst import DEFAULT_LOWER, DEFAULT_UPPER
    rng = np.random.default_rng(42)
    n_pass = 0
    n_total = 20
    for _ in range(n_total):
        # Random perturbation: each coeff in [0.5x, 1.5x] of default
        lower = DEFAULT_LOWER * rng.uniform(0.5, 1.5, 6)
        upper = DEFAULT_UPPER * rng.uniform(0.5, 1.5, 6)
        coeffs = np.concatenate([lower, upper])
        try:
            mesh = build_watertight_stl(coeffs)
            if mesh.is_watertight:
                n_pass += 1
        except Exception:
            pass
    # Expect at least 50% pass rate for mild perturbations
    assert n_pass >= n_total // 2, (
        f"only {n_pass}/{n_total} random CST vectors produced watertight meshes")


def test_load_coeffs_default():
    coeffs = load_cst_coefficients()
    assert coeffs.shape == (12,)
    from cfd_harness.surrogate.cst import DEFAULT_LOWER, DEFAULT_UPPER
    assert np.allclose(coeffs, np.concatenate([DEFAULT_LOWER, DEFAULT_UPPER]))


def test_load_coeffs_csv():
    csv = "0.1,0.1,0.15,0.15,0.15,0.05,0.2,0.3,0.3,0.3,0.3,0.05"
    coeffs = load_cst_coefficients(coeffs_csv=csv)
    assert coeffs.shape == (12,)
    assert coeffs[0] == pytest.approx(0.1)
    assert coeffs[-1] == pytest.approx(0.05)
