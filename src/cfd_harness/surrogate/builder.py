"""
builder.py -- CST 12-coefficient vector -> watertight 1-passage STL.

For M3 surrogate training we need 1-passage watertight STLs parameterized by
a 12-vector of CST coefficients. The pipeline:

  1. Generate a 2D airfoil outline (40 chordwise points per surface) via CST.
  2. Extrude the outline along the span (default z = 20 mm, hub-section
     constant -- 2D-slice approximation per M2 ground rules).
  3. Translate to the hub radius position.
  4. Export a watertight STL (is_watertight=True).

Solver-agnostic: pure Python + trimesh + shapely + cfd_harness.surrogate.cst.
For the multi-section 3D version (M3-S4) we would generate one outline per
spanwise section and loft; for M3 LHS we use the 2D-slice constant-extrude
approach (already proven watertight).

This module is the in-package implementation. ``scripts/build_r37_from_cst.py``
is a thin wrapper.
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import numpy as np

# R37 hub-section dimensions (from rotor37_geometry.py M2).
HUB_RADIUS_M = 0.15875     # m, R37 hub diameter / 2 (0.3175/2)
EXTRUDE_M = 0.020          # 20 mm axial passage depth
N_OUTLINE_POINTS = 40      # chordwise points per surface (40 lower + 39 upper = 79)
CHORD_M_DEFAULT = 0.0405   # 40.5 mm, R37 hub section chord
N_COEFFS = 12


def load_cst_coefficients(yaml_path: Optional[str] = None,
                          coeffs_csv: Optional[str] = None) -> np.ndarray:
    """Load 12-coefficient vector from yaml, csv, or cfd_harness default.

    Args:
        yaml_path: a gold-standard YAML with ``reference_values[0].value``
            as a 12-list.
        coeffs_csv: 12 comma-separated floats: A1..A6 lower, A7..A12 upper.
        (At least one of yaml_path / coeffs_csv is set; otherwise defaults.)

    Returns:
        np.ndarray of shape (12,) dtype float64.
    """
    from cfd_harness.surrogate.cst import DEFAULT_LOWER, DEFAULT_UPPER
    if yaml_path:
        import yaml
        with open(yaml_path, encoding="utf-8") as f:
            d = yaml.safe_load(f)
        coeffs = d["reference_values"][0]["value"]
        return np.array(coeffs, dtype=np.float64)
    if coeffs_csv:
        return np.array([float(x) for x in coeffs_csv.split(",")], dtype=np.float64)
    return np.concatenate([DEFAULT_LOWER, DEFAULT_UPPER])


def outline_to_ccw(outline: np.ndarray) -> np.ndarray:
    """Ensure the outline polygon is counter-clockwise (shoelace formula)."""
    s = 0.0
    n = len(outline)
    for i in range(n):
        x1, y1 = outline[i]
        x2, y2 = outline[(i + 1) % n]
        s += (x2 - x1) * (y2 + y1)
    if s > 0:  # clockwise
        return outline[::-1].copy()
    return outline


def build_watertight_stl(coeffs: np.ndarray,
                         n_outline: int = N_OUTLINE_POINTS,
                         extrude_m: float = EXTRUDE_M,
                         hub_radius_m: float = HUB_RADIUS_M,
                         chord_m: float = CHORD_M_DEFAULT):
    """Build a watertight 1-passage STL from 12 CST coefficients.

    Args:
        coeffs: 12-vector [A1..A6 lower, A7..A12 upper]
        n_outline: points per surface (default 40)
        extrude_m: axial depth (m, default 0.020)
        hub_radius_m: hub radius to position the section (m, default 0.15875)
        chord_m: physical chord length (m, default 0.0405)

    Returns:
        trimesh.Trimesh with is_watertight=True (caller should verify).

    Raises:
        ValueError: if the airfoil polygon is invalid even after buffer(0) repair.
    """
    from cfd_harness.surrogate.cst import CSTAirfoil
    import trimesh
    import trimesh.creation as trc
    from shapely.geometry import Polygon

    assert coeffs.shape == (N_COEFFS,), (
        f"expected 12 CST coeffs, got shape {coeffs.shape}"
    )

    af = CSTAirfoil.from_vector(coeffs)
    xy_norm = af.outline(n_points=n_outline)   # (79, 2)
    xy = xy_norm.copy()
    xy[:, 0] *= chord_m
    xy[:, 1] *= chord_m

    xy = outline_to_ccw(xy)
    poly = Polygon(xy)
    if not poly.is_valid:
        # Buffer 0 to repair minor self-intersections; if multi-piece, take
        # the largest piece (likely the outer boundary).
        fixed = poly.buffer(0)
        if fixed.geom_type == "MultiPolygon":
            poly = max(fixed.geoms, key=lambda g: g.area)
        else:
            poly = fixed
    if poly.geom_type == "MultiPolygon":
        # Should be rare after buffer(0) repair; take the largest piece.
        poly = max(poly.geoms, key=lambda g: g.area)
    if not (poly.is_valid and not poly.is_empty):
        raise ValueError(f"airfoil polygon invalid: {poly}")

    extruded = trc.extrude_polygon(poly, height=extrude_m)
    # Position: airfoil LE at origin, mid-chord at chord/2, section at hub_radius.
    extruded.apply_translation([chord_m / 2.0, hub_radius_m, 0.0])
    return extruded


def verify_watertight(mesh, label: str = "mesh") -> Dict[str, Any]:
    """Verify the watertight property + return a diagnostic dict."""
    return {
        "label": label,
        "n_vertices": int(len(mesh.vertices)),
        "n_faces": int(len(mesh.faces)),
        "n_edges_unique": int(len(mesh.edges_unique)),
        "is_watertight": bool(mesh.is_watertight),
        "is_winding_consistent": bool(mesh.is_winding_consistent),
        "volume_m3": float(mesh.volume) if mesh.is_watertight else float("nan"),
        "bounds_min": mesh.bounds[0].tolist(),
        "bounds_max": mesh.bounds[1].tolist(),
    }


def export_stl(mesh, out_path: str) -> int:
    """Write a trimesh mesh to STL and return the file size in bytes."""
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    mesh.export(out_path)
    return int(os.path.getsize(out_path))


__all__ = [
    "HUB_RADIUS_M",
    "EXTRUDE_M",
    "N_OUTLINE_POINTS",
    "CHORD_M_DEFAULT",
    "N_COEFFS",
    "load_cst_coefficients",
    "outline_to_ccw",
    "build_watertight_stl",
    "verify_watertight",
    "export_stl",
]
