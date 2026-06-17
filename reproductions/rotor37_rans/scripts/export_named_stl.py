"""Combine the 7 bc_*.stl into ONE multi-solid ASCII STL with named solids, so
STAR-CCM+ imports a single part with 7 named part-surfaces (inlet/outlet/hub/
shroud/blade/per1/per2). High precision keeps shared edges coincident for stitching."""
import glob, os
import numpy as np
import trimesh

GEOM = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\geom"
ORDER = ["inlet", "outlet", "hub", "shroud", "blade", "per1", "per2"]
out = GEOM + r"\fluid_passage_named.stl"

with open(out, "w") as fo:
    for name in ORDER:
        path = GEOM + f"\\bc_{name}.stl"
        if not os.path.exists(path):
            print("MISSING", path); continue
        m = trimesh.load(path)
        v = m.vertices; f = m.faces; n = m.face_normals
        fo.write(f"solid {name}\n")
        for ti, tri in enumerate(f):
            nx, ny, nz = n[ti]
            fo.write(f"  facet normal {nx:.9e} {ny:.9e} {nz:.9e}\n    outer loop\n")
            for vi in tri:
                x, y, z = v[vi]
                fo.write(f"      vertex {x:.9e} {y:.9e} {z:.9e}\n")
            fo.write("    endloop\n  endfacet\n")
        fo.write(f"endsolid {name}\n")
        print(f"  wrote solid {name}: {len(f)} facets")

print("named STL:", out, f"({os.path.getsize(out)//1024} KB)")
