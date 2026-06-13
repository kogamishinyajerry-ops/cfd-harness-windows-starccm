"""
FFD (Free-Form Deformation) for 3D blade sweeps.

Trivariate tensor-product B-spline FFD lattice. Default 5x5x5 = 125 control
points. We expose 3 operation families:

  1. ``bend_lattice(lattice, axis, k, loc)`` -- single-axis rotation around a
     line (e.g. blade axis for sweep / lean).
  2. ``twist_lattice(lattice, axis, k_per_length)`` -- linear twist around an
     axis (e.g. radial twist for blade pitch).
  3. ``translate_lattice(lattice, offset)`` -- uniform translation (e.g. chord
     expansion, thickness bump).

The FFD control point positions are the optimization variables. For M3 we
expose ``lattice_to_vector`` / ``vector_to_lattice`` so a future PCA reduction
(step "FFD(PCA 缩到 ~15)") can compress 125 vars to 10-15 vars downstream.

Reference:
  Sederberg, T. W., & Parry, S. R. (1986). "Free-form deformation of solid
    geometric models." SIGGRAPH Comput. Graph. 20(4), 151-160.
  Samareh, J. (2001). "Novel approach for aerospace shape optimization."
    AIAA-2001-0473.

This module is solver-agnostic (pure Python + numpy). No FFD lattice is
generated from external CSM files in M3 -- caller provides 3D points to deform.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np

# Default lattice size
DEFAULT_NU, DEFAULT_NV, DEFAULT_NW = 5, 5, 5  # 125 control points
DEFAULT_N_CTRL = DEFAULT_NU * DEFAULT_NV * DEFAULT_NW  # 125

# 3D control points per control point
N_DIM = 3


def make_lattice(origin: np.ndarray,
                 du: np.ndarray, nu: int,
                 dv: np.ndarray, nv: int,
                 dw: np.ndarray, nw: int) -> np.ndarray:
    """Build a (nu, nv, nw, 3) tensor-product lattice.

    origin: 3-vector for control point (0,0,0).
    du, dv, dw: 3-vectors giving the lattice cell edges (sizes).
    """
    origin = np.asarray(origin, dtype=np.float64)
    du = np.asarray(du, dtype=np.float64)
    dv = np.asarray(dv, dtype=np.float64)
    dw = np.asarray(dw, dtype=np.float64)
    assert origin.shape == (3,) and du.shape == (3,) and dv.shape == (3,) and dw.shape == (3,)

    lat = np.zeros((nu, nv, nw, 3), dtype=np.float64)
    for i in range(nu):
        for j in range(nv):
            for k in range(nw):
                lat[i, j, k] = origin + i * du + j * dv + k * dw
    return lat


def lattice_to_vector(lat: np.ndarray) -> np.ndarray:
    """Flatten (nu, nv, nw, 3) -> (3*nu*nv*nw,) in (i,j,k,dim) order."""
    lat = np.asarray(lat, dtype=np.float64)
    return lat.reshape(-1)


def vector_to_lattice(vec: np.ndarray, nu: int, nv: int, nw: int) -> np.ndarray:
    """Inverse of lattice_to_vector."""
    vec = np.asarray(vec, dtype=np.float64)
    assert vec.shape == (3 * nu * nv * nw,), (
        f"vec shape {vec.shape} != (3*{nu}*{nv}*{nw},)={3*nu*nv*nw}")
    return vec.reshape(nu, nv, nw, 3)


def bernstein3(n: int, i: int, t: np.ndarray) -> np.ndarray:
    """B_{i,n}(t) for 1D trivariate B-spline evaluation."""
    from math import comb
    return comb(n, i) * (t ** i) * ((1.0 - t) ** (n - i))


def deform_points(lat: np.ndarray, points: np.ndarray) -> np.ndarray:
    """Deform 3D points through a tensor-product B-spline FFD lattice.

    Uses uniform parameterization: t_u in [0,1] along lattice u (i index).
    Lattice cell edges du, dv, dw are inferred from control points.

    Args:
        lat: (nu, nv, nw, 3) control lattice.
        points: (N, 3) points to deform.

    Returns:
        (N, 3) deformed points.
    """
    lat = np.asarray(lat, dtype=np.float64)
    points = np.asarray(points, dtype=np.float64)
    assert lat.ndim == 4 and lat.shape[-1] == 3, f"lat bad shape {lat.shape}"
    assert points.ndim == 2 and points.shape[-1] == 3, f"points bad shape {points.shape}"

    nu, nv, nw, _ = lat.shape
    # Lattice extent (corner-to-corner) for parameterization: t, s, r in [0, 1]
    # over the bbox of the lattice. In an affine lattice with cell edges du, dv, dw,
    # the corner index is (nu-1) cells, (nv-1) cells, (nw-1) cells.
    extent = np.array([(nu - 1), (nv - 1), (nw - 1)], dtype=np.float64)  # in cell counts

    # Affine map: p = origin + t * (du) * (nu-1), so t = (p - origin) / ((nu-1) * du)
    # Use cell-edge vector A[k] = lat[1,0,0] - lat[0,0,0] = du, etc.
    A = np.zeros((3, 3), dtype=np.float64)
    A[0] = lat[1, 0, 0] - lat[0, 0, 0]  # du vector
    A[1] = lat[0, 1, 0] - lat[0, 0, 0]  # dv vector
    A[2] = lat[0, 0, 1] - lat[0, 0, 0]  # dw vector
    # Map point to parametric: tsr = (p - origin) / (extent * A[k]) component-wise
    # A is rows-stored (du, dv, dw). p - origin = sum_k tsr_k * A[k] for uniform tsr.
    # Solve via least squares (assuming non-degenerate A).
    Ainv = np.linalg.inv(A)

    rel = points - lat[0, 0, 0]  # (N, 3)
    tsr = rel @ Ainv
    # Normalize by extent to get [0, 1] parameter
    tsr = tsr / extent
    tsr = np.clip(tsr, 0.0, 1.0)

    # Trivariate Bernstein evaluation
    out = np.zeros_like(points)
    for i in range(nu):
        Bu = bernstein3(nu - 1, i, tsr[:, 0])
        for j in range(nv):
            Bv = bernstein3(nv - 1, j, tsr[:, 1])
            for k in range(nw):
                Bw = bernstein3(nw - 1, k, tsr[:, 2])
                B = Bu * Bv * Bw  # (N,)
                out += B[:, None] * lat[i, j, k]
    return out


# ---------- High-level operations on lattice ----------
def bend_lattice(lat: np.ndarray, axis_pivot: np.ndarray, axis_dir: np.ndarray,
                 angle_rad: float) -> np.ndarray:
    """Bend the lattice by rotating around an axis.

    Useful for blade sweep (rotate around axial line at hub).
    """
    lat = np.asarray(lat, dtype=np.float64).copy()
    axis_pivot = np.asarray(axis_pivot, dtype=np.float64)
    axis_dir = np.asarray(axis_dir, dtype=np.float64)
    axis_dir = axis_dir / (np.linalg.norm(axis_dir) + 1e-15)

    cos_a = np.cos(angle_rad)
    sin_a = np.sin(angle_rad)
    K = np.array([[0, -axis_dir[2], axis_dir[1]],
                  [axis_dir[2], 0, -axis_dir[0]],
                  [-axis_dir[1], axis_dir[0], 0]])
    R = np.eye(3) + sin_a * K + (1 - cos_a) * (K @ K)

    rel = lat.reshape(-1, 3) - axis_pivot
    rot = rel @ R.T
    new_pts = rot + axis_pivot
    return new_pts.reshape(lat.shape)


def twist_lattice(lat: np.ndarray, axis_pivot: np.ndarray, axis_dir: np.ndarray,
                  twist_per_length: float) -> np.ndarray:
    """Twist the lattice by rotating around axis, angle proportional to projection.

    Useful for blade pitch distribution along the span.
    """
    lat = np.asarray(lat, dtype=np.float64).copy()
    axis_pivot = np.asarray(axis_pivot, dtype=np.float64)
    axis_dir = np.asarray(axis_dir, dtype=np.float64)
    axis_dir = axis_dir / (np.linalg.norm(axis_dir) + 1e-15)

    flat = lat.reshape(-1, 3)
    rel = flat - axis_pivot
    proj = rel @ axis_dir  # projection along axis
    for idx in range(flat.shape[0]):
        angle = twist_per_length * proj[idx]
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        K = np.array([[0, -axis_dir[2], axis_dir[1]],
                      [axis_dir[2], 0, -axis_dir[0]],
                      [-axis_dir[1], axis_dir[0], 0]])
        R = np.eye(3) + sin_a * K + (1 - cos_a) * (K @ K)
        flat[idx] = rel[idx] @ R.T + axis_pivot
    return flat.reshape(lat.shape)


def translate_lattice(lat: np.ndarray, offset: np.ndarray) -> np.ndarray:
    """Uniform translation of all control points."""
    lat = lat.copy()
    lat += np.asarray(offset, dtype=np.float64)
    return lat


@dataclass
class FFDBlade:
    """Convenience wrapper: a 5x5x5 FFD lattice + standard blade operations."""
    lattice: np.ndarray
    pivot: np.ndarray
    axis: np.ndarray

    @classmethod
    def default_unit(cls) -> "FFDBlade":
        """Make a unit lattice (chord 0..1, span 0..1, thickness 0..1)."""
        lat = make_lattice(np.array([0.0, 0.0, 0.0]),
                            np.array([1.0, 0.0, 0.0]) / 4, DEFAULT_NU,
                            np.array([0.0, 1.0, 0.0]) / 4, DEFAULT_NV,
                            np.array([0.0, 0.0, 1.0]) / 4, DEFAULT_NW)
        return cls(lat, pivot=np.array([0.0, 0.0, 0.0]),
                   axis=np.array([0.0, 0.0, 1.0]))

    def sweep(self, angle_rad: float) -> None:
        self.lattice = bend_lattice(self.lattice, self.pivot, self.axis, angle_rad)

    def twist(self, twist_per_length: float) -> None:
        self.lattice = twist_lattice(self.lattice, self.pivot, self.axis, twist_per_length)

    def to_vector(self) -> np.ndarray:
        return lattice_to_vector(self.lattice)

    @classmethod
    def from_vector(cls, vec: np.ndarray,
                    pivot: np.ndarray, axis: np.ndarray) -> "FFDBlade":
        lat = vector_to_lattice(vec, DEFAULT_NU, DEFAULT_NV, DEFAULT_NW)
        return cls(lat, pivot, axis)
