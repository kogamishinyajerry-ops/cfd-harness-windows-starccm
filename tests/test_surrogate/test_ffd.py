"""
FFD (Free-Form Deformation) unit tests.

  1. Unit lattice construction (5x5x5, 125 ctrl pts)
  2. lattice_to_vector / vector_to_lattice round-trip
  3. Trivariate Bernstein partition of unity (sum = 1)
  4. Identity FFD: deform_points with uniform lattice = identity
  5. translate_lattice: rigid shift
  6. bend_lattice: rotation around axis preserves distance to axis
  7. twist_lattice: rotation around axis
  8. FFDBlade: sweep + twist + to_vector
"""
from __future__ import annotations

import numpy as np
import pytest

from cfd_harness.surrogate.ffd import (
    DEFAULT_NU, DEFAULT_NV, DEFAULT_NW, DEFAULT_N_CTRL,
    make_lattice, lattice_to_vector, vector_to_lattice,
    deform_points, bernstein3,
    bend_lattice, twist_lattice, translate_lattice,
    FFDBlade,
)


# ---------- 1. Unit lattice ----------
def test_default_dims():
    assert (DEFAULT_NU, DEFAULT_NV, DEFAULT_NW) == (5, 5, 5)
    assert DEFAULT_N_CTRL == 125


def test_make_lattice_shape():
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 5,
                       np.array([0.0, 1.0, 0.0]), 5,
                       np.array([0.0, 0.0, 1.0]), 5)
    assert lat.shape == (5, 5, 5, 3)
    assert np.allclose(lat[0, 0, 0], [0, 0, 0])
    assert np.allclose(lat[-1, -1, -1], [4, 4, 4])
    assert np.allclose(lat[1, 0, 0], [1, 0, 0])
    assert np.allclose(lat[0, 1, 0], [0, 1, 0])
    assert np.allclose(lat[0, 0, 1], [0, 0, 1])


# ---------- 2. Round-trip ----------
def test_lattice_vector_round_trip():
    lat = make_lattice(np.array([1.0, 2.0, 3.0]),
                       np.array([0.1, 0.0, 0.0]), 4,
                       np.array([0.0, 0.2, 0.0]), 3,
                       np.array([0.0, 0.0, 0.3]), 2)
    vec = lattice_to_vector(lat)
    assert vec.shape == (4 * 3 * 2 * 3,)
    lat2 = vector_to_lattice(vec, 4, 3, 2)
    assert np.allclose(lat, lat2)


def test_vector_wrong_size_rejected():
    with pytest.raises(AssertionError):
        vector_to_lattice(np.zeros(300), 5, 5, 5)  # 300 != 375


# ---------- 3. Trivariate Bernstein partition of unity ----------
def test_trivariate_partition_of_unity():
    t = np.array([0.1, 0.3, 0.5, 0.7, 0.9])
    for n in [3, 4, 5]:
        s = sum(bernstein3(n, i, t) for i in range(n + 1))
        assert np.allclose(s, 1.0), f"n={n} does not sum to 1: {s}"


# ---------- 4. Identity FFD ----------
def test_identity_deform():
    # Lattice spans (0,0,0) to (4,4,4). A point in the bbox should map to itself.
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 5,
                       np.array([0.0, 1.0, 0.0]), 5,
                       np.array([0.0, 0.0, 1.0]), 5)
    # Sample points along the lattice domain
    pts = np.array([[0.0, 0.0, 0.0],
                    [1.0, 2.0, 3.0],   # interior point
                    [2.0, 2.0, 2.0],   # mid (lattice center)
                    [4.0, 4.0, 4.0]])  # corner
    out = deform_points(lat, pts)
    assert out.shape == pts.shape
    assert np.allclose(out, pts, atol=1e-9), f"identity FFD failed: {out}"


# ---------- 5. translate_lattice ----------
def test_translate_lattice():
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 3,
                       np.array([0.0, 1.0, 0.0]), 3,
                       np.array([0.0, 0.0, 1.0]), 3)
    new = translate_lattice(lat, np.array([1.0, 2.0, 3.0]))
    assert np.allclose(new[0, 0, 0], [1, 2, 3])
    assert np.allclose(new - lat, np.array([1.0, 2.0, 3.0]))


# ---------- 6. bend_lattice preserves distance to axis ----------
def test_bend_preserves_distance_to_axis():
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 3,
                       np.array([0.0, 1.0, 0.0]), 3,
                       np.array([0.0, 0.0, 1.0]), 3)
    pivot = np.array([0.0, 0.0, 0.0])
    axis = np.array([0.0, 0.0, 1.0])
    flat = lat.reshape(-1, 3)
    # Distance to axis (z-axis): sqrt(x^2 + y^2)
    dist_before = np.linalg.norm(flat[:, :2], axis=1)
    new = bend_lattice(lat, pivot, axis, np.deg2rad(30.0))
    flat2 = new.reshape(-1, 3)
    dist_after = np.linalg.norm(flat2[:, :2], axis=1)
    assert np.allclose(dist_before, dist_after, atol=1e-12)


# ---------- 7. twist_lattice ----------
def test_twist_zero_is_identity():
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 3,
                       np.array([0.0, 1.0, 0.0]), 3,
                       np.array([0.0, 0.0, 1.0]), 3)
    new = twist_lattice(lat, np.array([0.0, 0.0, 0.0]),
                        np.array([0.0, 0.0, 1.0]), twist_per_length=0.0)
    assert np.allclose(new, lat)


def test_twist_preserves_distance_to_axis():
    lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                       np.array([1.0, 0.0, 0.0]), 3,
                       np.array([0.0, 1.0, 0.0]), 3,
                       np.array([0.0, 0.0, 1.0]), 3)
    pivot = np.array([0.0, 0.0, 0.0])
    axis = np.array([0.0, 0.0, 1.0])
    flat = lat.reshape(-1, 3)
    dist_before = np.linalg.norm(flat[:, :2], axis=1)
    new = twist_lattice(lat, pivot, axis, twist_per_length=0.5)
    flat2 = new.reshape(-1, 3)
    dist_after = np.linalg.norm(flat2[:, :2], axis=1)
    assert np.allclose(dist_before, dist_after, atol=1e-12)


# ---------- 8. FFDBlade ----------
def test_ffdblade_default_unit():
    blade = FFDBlade.default_unit()
    assert blade.lattice.shape == (5, 5, 5, 3)
    assert np.allclose(blade.lattice[0, 0, 0], [0, 0, 0])
    assert np.allclose(blade.lattice[-1, -1, -1], [1, 1, 1])


def test_ffdblade_sweep_modifies_lattice():
    blade = FFDBlade.default_unit()
    before = blade.lattice.copy()
    blade.sweep(np.deg2rad(15.0))
    assert not np.allclose(blade.lattice, before)
    # but origin (0,0,0) with axis (0,0,1) is on the axis -> unchanged
    assert np.allclose(blade.lattice[0, 0, 0], [0, 0, 0], atol=1e-12)


def test_ffdblade_vector_round_trip():
    blade = FFDBlade.default_unit()
    vec = blade.to_vector()
    assert vec.shape == (375,)
    blade2 = FFDBlade.from_vector(vec, blade.pivot, blade.axis)
    assert np.allclose(blade2.lattice, blade.lattice)
