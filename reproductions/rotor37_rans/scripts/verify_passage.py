"""Verify the reconstructed passage: body count + per-boundary geometric extents,
so we trust the BC labels before wiring the STAR-CCM+ macro."""
import glob, os
import numpy as np
import trimesh

GEOM = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\geom"

def stats(m):
    c = m.triangles_center
    r = np.sqrt(c[:,0]**2 + c[:,1]**2); th = np.degrees(np.arctan2(c[:,1], c[:,0])); z = c[:,2]
    n = m.face_normals
    # dominant normal component
    comp = ["x","y","z"][int(np.argmax(np.abs(n).mean(axis=0)))]
    return r, th, z, comp

fluid = trimesh.load(GEOM + r"\fluid_passage.stl")
bodies = fluid.split(only_watertight=False)
print(f"fluid bodies={len(bodies)}  (expect 1)  total_vol={fluid.volume:.4e}")
print(f"fluid bounds z=[{fluid.bounds[0,2]:.4f},{fluid.bounds[1,2]:.4f}]\n")

print(f"{'group':8} {'faces':>6} {'r[min,max]':>20} {'z[min,max]':>20} {'theta[min,max]deg':>22} {'norm':>5}")
for f in sorted(glob.glob(GEOM + r"\bc_*.stl")):
    name = os.path.basename(f)[3:-4]
    m = trimesh.load(f)
    r, th, z, comp = stats(m)
    print(f"{name:8} {len(m.faces):>6} [{r.min():.4f},{r.max():.4f}]   "
          f"[{z.min():+.4f},{z.max():+.4f}]   [{th.min():7.2f},{th.max():7.2f}]   {comp:>5}")
