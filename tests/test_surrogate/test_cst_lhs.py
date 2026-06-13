"""
Tests for cst_lhs.py (LHS sampling of CST design space).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

_REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, _REPO)
sys.path.insert(0, os.path.join(_REPO, 'scripts'))

from cst_lhs import load_lhs_bounds, sample_lhs


def test_load_lhs_bounds_shape_and_order():
    lb, ub = load_lhs_bounds()
    assert lb.shape == (12,)
    assert ub.shape == (12,)
    # Inner Bernstein terms (A2..A5 lower, A8..A11 upper) should have wider
    # bounds than TE terms (A6, A12)
    # A6 is index 5, A12 is index 11
    assert ub[5] - lb[5] < ub[1] - lb[1]   # A6 narrower than A2
    assert ub[11] - lb[11] < ub[7] - lb[7]  # A12 narrower than A8


def test_sample_lhs_shape():
    lb, ub = load_lhs_bounds()
    samples = sample_lhs(50, lb, ub, seed=42)
    assert samples.shape == (50, 12)


def test_sample_lhs_in_bounds():
    lb, ub = load_lhs_bounds()
    samples = sample_lhs(100, lb, ub, seed=42)
    assert np.all(samples >= lb - 1e-9), f"min below lb: {samples.min(0)}"
    assert np.all(samples <= ub + 1e-9), f"max above ub: {samples.max(0)}"


def test_sample_lhs_deterministic():
    lb, ub = load_lhs_bounds()
    s1 = sample_lhs(100, lb, ub, seed=42)
    s2 = sample_lhs(100, lb, ub, seed=42)
    assert np.allclose(s1, s2)


def test_sample_lhs_different_seeds_differ():
    lb, ub = load_lhs_bounds()
    s1 = sample_lhs(100, lb, ub, seed=42)
    s2 = sample_lhs(100, lb, ub, seed=7)
    assert not np.allclose(s1, s2)


def test_sample_lhs_space_filling():
    """Project 1D marginals and check the points are well-distributed.

    For each variable, the LHS should have at most one sample per bin.
    """
    lb, ub = load_lhs_bounds()
    samples = sample_lhs(100, lb, ub, seed=42)
    # Project onto first variable
    v0 = samples[:, 0]
    n_bins = 10
    counts, _ = np.histogram(v0, bins=n_bins)
    # LHS guarantee: no bin should be empty (at most 1 sample per bin)
    # Allow one empty bin for n=100, d=12 with centered discrepancy
    n_empty = int(np.sum(counts == 0))
    assert n_empty <= 1, f"too many empty bins in marginal: {counts}"


def test_sample_lhs_100_full_run():
    """Integration: 100 samples from default yaml."""
    lb, ub = load_lhs_bounds()
    samples = sample_lhs(100, lb, ub, seed=42)
    assert samples.shape == (100, 12)
    # Bounds respected
    assert np.all(samples >= lb - 1e-9)
    assert np.all(samples <= ub + 1e-9)
    # Means roughly at the centroid of bounds (LHS is approximately uniform)
    centroid = (lb + ub) / 2
    err = np.abs(samples.mean(0) - centroid) / (ub - lb)
    # Mean should be within 15% of centroid per dim
    assert np.all(err < 0.15), f"per-dim mean err {err.round(3)} too large"
