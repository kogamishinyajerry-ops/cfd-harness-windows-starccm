"""Lid-driven cavity STL generator.

Generates an ASCII STL for a 3D box cavity of size
(size_m, size_m, thickness_m). The cavity is centered at the
origin with the box extents spanning [-size/2, +size/2] in X and Y,
and [-thickness/2, +thickness/2] in Z (thin extrusion in Z for
2D-like behavior).

The STL is a simple 12-triangle box (6 faces, 2 triangles each),
which is the simplest closed manifold STAR-CCM+ can mesh + solve.

Output
------
Writes ``<out_dir>/lid_driven_cavity.stl``.

The mesh is deliberately tiny in Z (default 0.01m) so the
LidDrivenCavity.java macro can run it as a 2D-like simulation
in STAR-CCM+ 19.02 (which doesn't expose the solidmodeler package
the same way as newer versions; the user's existing macros all
use PartImportManager.importStlPart, so we follow that pattern).
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple


def write_lid_driven_cavity_stl(
    out_path: Path,
    size_m: float = 1.0,
    thickness_m: float = 0.01,
) -> Path:
    """Write a box cavity STL to ``out_path``.

    Returns the path written.
    """
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # 8 vertices of a box centered at origin
    hx = size_m / 2.0
    hy = size_m / 2.0
    hz = thickness_m / 2.0
    verts = {
        # 4 corners at z=+hz (top)
        "TFL": (-hx, -hy, +hz),  # top face, front-left  (low x, low y)
        "TFR": (+hx, -hy, +hz),
        "TBR": (+hx, +hy, +hz),
        "TBL": (-hx, +hy, +hz),
        # 4 corners at z=-hz (bottom)
        "BFL": (-hx, -hy, -hz),
        "BFR": (+hx, -hy, -hz),
        "BBR": (+hx, +hy, -hz),
        "BBL": (-hx, +hy, -hz),
    }

    # 12 triangles (2 per face × 6 faces)
    # Each triangle: 3 vertices + normal (computed from winding).
    # Right-hand rule: outward-pointing normal.
    triangles: list = []

    def add_face(name_a: str, name_b: str, name_c: str) -> None:
        """Add a triangle to the STL (vertex order = right-hand rule)."""
        va, vb, vc = verts[name_a], verts[name_b], verts[name_c]
        # Normal: (b - a) × (c - a)
        e1 = (vb[0] - va[0], vb[1] - va[1], vb[2] - va[2])
        e2 = (vc[0] - va[0], vc[1] - va[1], vc[2] - va[2])
        n = (
            e1[1] * e2[2] - e1[2] * e2[1],
            e1[2] * e2[0] - e1[0] * e2[2],
            e1[0] * e2[1] - e1[1] * e2[0],
        )
        nlen = math.sqrt(n[0] ** 2 + n[1] ** 2 + n[2] ** 2)
        if nlen > 0:
            n = (n[0] / nlen, n[1] / nlen, n[2] / nlen)
        triangles.append((n, va, vb, vc))

    # -X face (left, x = -hx) : normal -X
    add_face("BFL", "BBL", "TBL")
    add_face("BFL", "TBL", "TFL")
    # +X face (right, x = +hx) : normal +X
    add_face("BFR", "TFR", "TBR")
    add_face("BFR", "TBR", "BBR")
    # -Y face (front, y = -hy) : normal -Y
    add_face("BFL", "TFL", "TFR")
    add_face("BFL", "TFR", "BFR")
    # +Y face (back, y = +hy) : normal +Y
    add_face("BBL", "BBR", "TBR")
    add_face("BBL", "TBR", "TBL")
    # -Z face (bottom, z = -hz) : normal -Z
    add_face("BFL", "BFR", "BBR")
    add_face("BFL", "BBR", "BBL")
    # +Z face (top, z = +hz) : normal +Z
    add_face("TFL", "TBL", "TBR")
    add_face("TFL", "TBR", "TFR")

    # Write ASCII STL
    with out_path.open("w", encoding="ascii", newline="\n") as f:
        f.write("solid lid_driven_cavity\n")
        for n, va, vb, vc in triangles:
            f.write(f"  facet normal {n[0]:.6e} {n[1]:.6e} {n[2]:.6e}\n")
            f.write("    outer loop\n")
            for vx, vy, vz in (va, vb, vc):
                f.write(f"      vertex {vx:.6e} {vy:.6e} {vz:.6e}\n")
            f.write("    endloop\n")
            f.write("  endfacet\n")
        f.write("endsolid lid_driven_cavity\n")
    return out_path


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", default="D:/StarCCM Codebuddy/Cases/lid_driven_cavity.stl")
    p.add_argument("--size", type=float, default=1.0)
    p.add_argument("--thickness", type=float, default=0.01)
    a = p.parse_args()
    out = write_lid_driven_cavity_stl(Path(a.out), size_m=a.size, thickness_m=a.thickness)
    print(f"wrote {out} ({out.stat().st_size} bytes)")
