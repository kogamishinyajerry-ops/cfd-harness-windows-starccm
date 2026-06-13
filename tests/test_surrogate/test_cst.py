"""
CST (Class-Shape Transformation) unit tests.

Smoke + correctness:
  1. Defaults load, shape OK
  2. Outline is closed (first == last) and monotonic in x
  3. Bernstein basis sums to 1 (partition of unity)
  4. Class function vanishes at LE/TE
  5. Rotor-37 default gives realistic thickness / camber
  6. Vector round-trip preserves airfoil
"""
from __future__ import annotations

import numpy as np
import pytest

from cfd_harness.surrogate.cst import (
    DEFAULT_LOWER, DEFAULT_UPPER, N1_DEFAULT, N2_DEFAULT, N_VARS,
    cst_class, cst_shape, bernstein,
    CSTAirfoil, vector_to_airfoil, airfoil_to_vector,
)


# ---------- 1. Defaults + shape ----------
def test_defaults_shape():
    assert DEFAULT_LOWER.shape == (6,)
    assert DEFAULT_UPPER.shape == (6,)
    af = CSTAirfoil()
    assert af.coeffs.shape == (12,)
    assert af.n1 == N1_DEFAULT
    assert af.n2 == N2_DEFAULT


def test_invalid_n_coeffs_rejected():
    with pytest.raises(AssertionError):
        CSTAirfoil(lower=np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7]),
                   upper=DEFAULT_UPPER.copy())


# ---------- 2. Outline closed + monotonic ----------
def test_outline_closed():
    af = CSTAirfoil()
    xy = af.outline(n_points=40)
    # 40 lower (TE..LE) + 39 upper (LE..TE skipping LE duplicate) = 79.
    # Last point is upper[end]=TE which equals lower[0]=TE -> already closed.
    assert xy.shape[0] == 79, f"expected 79 (40+39), got {xy.shape[0]}"
    assert np.allclose(xy[0], xy[-1]), f"outline not closed: {xy[0]} vs {xy[-1]}"


def test_outline_x_monotonic_lower_then_upper():
    af = CSTAirfoil()
    xy = af.outline(n_points=40)
    n = 40
    x_lower = xy[:n, 0]  # TE -> LE (decreasing)
    x_upper = xy[n:79, 0]  # LE -> TE (increasing, 39 pts)
    assert np.all(np.diff(x_lower) < 0), "lower x should decrease (TE->LE)"
    assert np.all(np.diff(x_upper) > 0), "upper x should increase (LE->TE)"


# ---------- 3. Bernstein partition of unity ----------
def test_bernstein_partition_of_unity():
    psi = np.linspace(0, 1, 50)
    for n in [3, 5, 6, 8]:
        s = sum(bernstein(n, i, psi) for i in range(n + 1))
        assert np.allclose(s, 1.0), f"Bernstein n={n} does not sum to 1"


# ---------- 4. Class function vanishes at endpoints ----------
def test_cst_class_vanishes_at_endpoints():
    psi = np.array([0.0, 0.001, 0.5, 0.999, 1.0])
    C = cst_class(psi)
    assert C[0] == 0.0  # psi=0
    assert C[-1] == 0.0  # psi=1
    assert C[0] == pytest.approx(0.0, abs=0.0)
    assert C[-1] == pytest.approx(0.0, abs=0.0)
    # inside
    assert C[2] > 0.0


# ---------- 5. Realistic thickness / camber ----------
def test_default_thickness_in_range():
    af = CSTAirfoil()
    t = af.max_thickness()
    assert 0.05 < t < 0.25, f"thickness {t:.4f} out of realistic 5-25%"


def test_default_camber_in_range():
    af = CSTAirfoil()
    c = af.max_camber()
    assert -0.05 < c < 0.10, f"camber {c:.4f} out of realistic -5..+10%"


# ---------- 6. Vector round-trip ----------
def test_vector_round_trip():
    af = CSTAirfoil()
    v = airfoil_to_vector(af)
    assert v.shape == (N_VARS,)
    af2 = vector_to_airfoil(v)
    assert np.allclose(af2.coeffs, af.coeffs)
    xy1 = af.outline()
    xy2 = af2.outline()
    assert np.allclose(xy1, xy2)


def test_from_vector_rejects_wrong_size():
    with pytest.raises(ValueError):
        vector_to_airfoil(np.array([0.1] * 11))


def test_to_scaling_offsets_and_chord():
    af = CSTAirfoil()
    xy = af.to_scaling(chord=2.0, x_offset=0.5, y_offset=0.1)
    assert xy.shape[0] == 79
    # first point: psi=1.0 (TE) -> x = 0.5+2 = 2.5, y = 0.1
    assert xy[0, 0] == pytest.approx(2.5, abs=1e-12)
    assert xy[0, 1] == pytest.approx(0.1, abs=1e-12)
