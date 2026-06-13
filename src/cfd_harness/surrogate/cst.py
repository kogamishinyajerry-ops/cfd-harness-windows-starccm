"""
CST (Class-Shape Transformation) airfoil parameterization.

Bruneau-style CST with N1=0.5, N2=1.0 leading/trailing edge shape factors.
12 variables = 6 lower Bernstein + 6 upper Bernstein coefficients.

Reference:
  Kulfan, B. (2008). "Universal Parametric Geometry Representation Method."
    Journal of Aircraft, 45(1), 142-158. doi:10.2514/1.29958

This module is solver-agnostic (pure Python + numpy). It produces a chord-
normalized 2D airfoil outline. Section-level meshing / 3D extrusion lives
in build_r37_from_cst.py / ffd.py.

Notation:
  psi in [0, 1] = chordwise parameter (0 = LE, 1 = TE)
  y(psi) = C(psi) * S(psi)
  C(psi) = psi^N1 * (1-psi)^N2              (class function)
  S(psi) = sum_{i=1..N} A_i * B_{i,N-1}(psi) (shape function, Bernstein)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np

# CST shape factors (Kulfan 2008 default)
N1_DEFAULT = 0.5
N2_DEFAULT = 1.0

# 12 variables = 6 lower (A1..A6) + 6 upper (A7..A12)
N_COEFF_LOWER = 6
N_COEFF_UPPER = 6
N_VARS = N_COEFF_LOWER + N_COEFF_UPPER  # 12

# Defaults: 12% cambered, ~12% thick, Rotor-37-ish baseline
# Lower: thin trailing edge, gentle suction
DEFAULT_LOWER = np.array([
    0.1186, 0.1181, 0.1561, 0.1454, 0.1500, 0.0500
], dtype=np.float64)
# Upper: pressure side bump near LE
DEFAULT_UPPER = np.array([
    0.2222, 0.2872, 0.2810, 0.2798, 0.2718, 0.0500
], dtype=np.float64)


def bernstein(n: int, i: int, psi: np.ndarray) -> np.ndarray:
    """B_{i,n}(psi) = C(n,i) * psi^i * (1-psi)^(n-i)."""
    from math import comb
    return comb(n, i) * (psi ** i) * ((1.0 - psi) ** (n - i))


def cst_class(psi: np.ndarray, n1: float = N1_DEFAULT, n2: float = N2_DEFAULT) -> np.ndarray:
    """C(psi) = psi^n1 * (1-psi)^n2  (chord-normalized class function)."""
    psi = np.clip(psi, 0.0, 1.0)
    return (psi ** n1) * ((1.0 - psi) ** n2)


def cst_shape(psi: np.ndarray, coeffs: np.ndarray) -> np.ndarray:
    """S(psi) = sum_{i=1..N} A_i * B_{i,N-1}(psi)."""
    n = len(coeffs)
    s = np.zeros_like(psi, dtype=np.float64)
    for i in range(n):
        s = s + coeffs[i] * bernstein(n - 1, i, psi)
    return s


@dataclass
class CSTAirfoil:
    """A 2D airfoil defined by 12 CST coefficients (6 lower + 6 upper).

    Use :py:meth:`outline` to get a chord-normalized (x, y) array.
    Use :py:meth:`to_scaling` to scale to physical chord and pitch.
    """
    lower: np.ndarray = field(default_factory=lambda: DEFAULT_LOWER.copy())
    upper: np.ndarray = field(default_factory=lambda: DEFAULT_UPPER.copy())
    n1: float = N1_DEFAULT
    n2: float = N2_DEFAULT

    def __post_init__(self) -> None:
        self.lower = np.asarray(self.lower, dtype=np.float64)
        self.upper = np.asarray(self.upper, dtype=np.float64)
        assert self.lower.shape == (N_COEFF_LOWER,), (
            f"lower must be {N_COEFF_LOWER} coeffs, got {self.lower.shape}")
        assert self.upper.shape == (N_COEFF_UPPER,), (
            f"upper must be {N_COEFF_UPPER} coeffs, got {self.upper.shape}")
        assert self.n1 >= 0.0 and self.n2 >= 0.0, "n1, n2 must be non-negative"

    @property
    def coeffs(self) -> np.ndarray:
        """12-variable parameter vector [A1..A6 lower | A7..A12 upper]."""
        return np.concatenate([self.lower, self.upper])

    @classmethod
    def from_vector(cls, vec: np.ndarray, n1: float = N1_DEFAULT, n2: float = N2_DEFAULT) -> "CSTAirfoil":
        """Construct from 12-variable vector."""
        vec = np.asarray(vec, dtype=np.float64)
        if vec.shape != (N_VARS,):
            raise ValueError(f"vector must be shape ({N_VARS},), got {vec.shape}")
        return cls(lower=vec[:N_COEFF_LOWER].copy(),
                   upper=vec[N_COEFF_LOWER:].copy(),
                   n1=n1, n2=n2)

    def outline(self, n_points: int = 40) -> np.ndarray:
        """Return chord-normalized outline as Nx2 (x, y), TE closed.

        Convention:
          Lower surface psi 1->0 (trailing edge to leading edge)
          Upper surface psi 0->1 (leading edge to trailing edge)
        Closes at TE (last point == first point).
        """
        assert n_points >= 4, "n_points must be >= 4"
        psi_lower = np.linspace(1.0, 0.0, n_points)  # TE -> LE
        psi_upper = np.linspace(0.0, 1.0, n_points)  # LE -> TE

        y_lower = cst_class(psi_lower, self.n1, self.n2) * cst_shape(psi_lower, self.lower)
        y_upper = cst_class(psi_upper, self.n1, self.n2) * cst_shape(psi_upper, self.upper)

        xy_lower = np.column_stack([psi_lower, y_lower])  # TE->LE (40 pts)
        xy_upper = np.column_stack([psi_upper, y_upper])  # LE->TE (40 pts)
        # Concatenate lower (TE->LE) then upper (LE->TE, skip first LE duplicate).
        # Lower has 40 pts: TE..LE inclusive.  Upper has 40 pts: LE..TE inclusive.
        # Drop upper[0] (the LE point already in lower[-1]) -> 40+39 = 79 pts.
        # Then append xy_upper[-1] (TE) and outline[0] (TE) to close the loop -> 81.
        outline = np.vstack([xy_lower, xy_upper[1:, :]])  # 79 pts, ends at TE
        # Close the loop: append the first TE point as the last point -> 80 pts
        if not np.allclose(outline[0], outline[-1]):
            outline = np.vstack([outline, outline[0:1, :]])
        return outline

    def to_scaling(self, chord: float, x_offset: float = 0.0, y_offset: float = 0.0) -> np.ndarray:
        """Scale chord-normalized outline to physical coordinates."""
        xy = self.outline()
        xy = xy.copy()
        xy[:, 0] = xy[:, 0] * chord + x_offset
        xy[:, 1] = xy[:, 1] * chord + y_offset
        return xy

    def max_thickness(self, n_samples: int = 200) -> float:
        """Max thickness / chord, evaluated on chord-normalized coordinates."""
        psi = np.linspace(0.0, 1.0, n_samples)
        y_lower = cst_class(psi, self.n1, self.n2) * cst_shape(psi, self.lower)
        y_upper = cst_class(psi, self.n1, self.n2) * cst_shape(psi, self.upper)
        return float(np.max(y_upper - y_lower))

    def max_camber(self, n_samples: int = 200) -> float:
        """Max camber / chord."""
        psi = np.linspace(0.0, 1.0, n_samples)
        y_lower = cst_class(psi, self.n1, self.n2) * cst_shape(psi, self.lower)
        y_upper = cst_class(psi, self.n1, self.n2) * cst_shape(psi, self.upper)
        return float(np.max((y_upper + y_lower) / 2.0))


def vector_to_airfoil(vec: Iterable[float], n1: float = N1_DEFAULT, n2: float = N2_DEFAULT) -> CSTAirfoil:
    """Convenience: convert iterable of 12 floats to CSTAirfoil."""
    return CSTAirfoil.from_vector(np.asarray(list(vec), dtype=np.float64), n1=n1, n2=n2)


def airfoil_to_vector(af: CSTAirfoil) -> np.ndarray:
    """Convenience: extract 12-float vector from CSTAirfoil."""
    return af.coeffs.copy()
