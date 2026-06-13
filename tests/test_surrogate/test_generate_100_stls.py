"""
Tests for generate_100_stls.py (end-to-end M3 pipeline).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'scripts'))

from generate_100_stls import load_lhs_npy, build_stl, verify_stl


LHS_PATH = os.path.join(_REPO, 'stl_samples', 'lhs', 'lhs_samples.npy')


@pytest.fixture(scope='module')
def samples():
    if not os.path.exists(LHS_PATH):
        pytest.skip(f"LHS samples not present at {LHS_PATH}. Run cst_lhs.py first.")
    return load_lhs_npy(LHS_PATH)


def test_load_lhs_npy_shape(samples):
    assert samples.ndim == 2
    assert samples.shape[1] == 12
    assert samples.shape[0] >= 100


def test_stl_batch_100_watertight(samples, tmp_path):
    """Generate 100 STLs to a temp dir and verify all are watertight."""
    out_dir = tmp_path / 'stl'
    out_dir.mkdir()
    n_pass = 0
    for i, coeffs in enumerate(samples[:100]):
        try:
            mesh = build_stl(coeffs)
            info = verify_stl(mesh)
            assert info['n_faces'] >= 4
            if info['is_watertight']:
                n_pass += 1
        except Exception:
            pass
    # Expect 100/100 (the polygon repair logic in build_r37_from_cst
    # should handle all cases).
    assert n_pass == 100, f"only {n_pass}/100 watertight"


def test_stl_batch_volume_distribution(samples, tmp_path):
    """Sample volumes should be within a physical range."""
    volumes = []
    for coeffs in samples[:20]:
        mesh = build_stl(coeffs)
        if mesh.is_watertight:
            volumes.append(float(mesh.volume))
    # Volumes: 1-3 cm^3 typically for hub-section prisms
    assert all(1e-7 < v < 1e-3 for v in volumes), (
        f"volumes out of range: {volumes}")
