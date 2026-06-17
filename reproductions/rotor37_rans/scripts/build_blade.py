"""Step 1 of fluid-domain reconstruction: build a WATERTIGHT blade solid from the
baseline Rotor 37 point cloud (sample 0).

Input array layout (verified): sample0 shape = (2, 9, 112, 4)
  axis 0: surface  -> 0=suction, 1=pressure
  axis 1: section  -> 9 spanwise sections, hub(0) -> tip(8)
  axis 2: point    -> 112 points along chord
  axis 3: (x, y, z, label);  rotation axis = z
Point ordering (verified): suction[0]=LE..suction[111]=TE ; pressure[0]=TE..pressure[111]=LE
  (suction[0] == pressure[111] == LE)

Ring per section (no duplicate seam, N=222): suction(LE->TE, 112) + pressure(1..110, TE->LE side).
Side walls = loft adjacent rings. End caps = suction<->pressure strip. Validate with trimesh.
"""
import os
import numpy as np
import trimesh

ASSETS = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\assets"
OUT = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\geom"
NPY = ASSETS + r"\deeplabs_rotor37_geometries_1.npy"

NCH = 112          # chordwise points per surface
NRING = 2 * NCH - 2  # 222: drop shared LE and TE seam duplicates

def ring_of(s0, k):
    """Closed ring (NRING,3): suction LE->TE then pressure interior (TE-side -> LE-side)."""
    suction = s0[0, k, :, :3]        # LE->TE, 112
    pressure = s0[1, k, :, :3]       # TE->LE, 112  (pressure[0]=TE, pressure[111]=LE)
    # ring = suction[0..111] + pressure[1..110]
    return np.vstack([suction, pressure[1:NCH-1]])  # 112 + 110 = 222

def pf_ringidx(i):
    """Ring index of pressure-side point at chord station i (i=0..111, LE->TE)."""
    # pressure LE->TE = pressure_raw[::-1]; map to ring indices
    if i == 0:
        return 0          # LE == suction[0]
    if i == NCH - 1:
        return NCH - 1    # TE == suction[111]
    return NRING - i      # interior pressure: 222 - i

def main():
    os.makedirs(OUT, exist_ok=True)
    arr = np.load(NPY, mmap_mode="r")
    s0 = np.asarray(arr[0])
    nsec = s0.shape[1]

    rings = np.array([ring_of(s0, k) for k in range(nsec)])  # (9,222,3)
    verts = rings.reshape(-1, 3)
    N = NRING
    def vid(k, i):
        return k * N + (i % N)

    faces = []
    # side walls (loft)
    for k in range(nsec - 1):
        for i in range(N):
            a, b = vid(k, i), vid(k, i + 1)
            c, d = vid(k + 1, i + 1), vid(k + 1, i)
            faces.append([a, b, c]); faces.append([a, c, d])

    # end caps: suction(i)<->pressure(i) strip, i=0..110
    def cap(k):
        cf = []
        for i in range(NCH - 1):
            s_a, s_b = vid(k, i), vid(k, i + 1)
            p_a, p_b = vid(k, pf_ringidx(i)), vid(k, pf_ringidx(i + 1))
            cf.append([s_a, s_b, p_b]); cf.append([s_a, p_b, p_a])
        return cf
    faces.extend(cap(0))          # hub end
    faces.extend(cap(nsec - 1))   # tip end

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=True)
    mesh.merge_vertices()
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()

    print(f"BLADE: verts={len(mesh.vertices)} faces={len(mesh.faces)}")
    print(f"  watertight={mesh.is_watertight}  winding_consistent={mesh.is_winding_consistent}")
    print(f"  volume={mesh.volume:.4e} m^3")
    print(f"  euler_number={mesh.euler_number} (2 => genus-0 closed)")
    b = mesh.bounds
    print(f"  bounds x[{b[0,0]:+.4f},{b[1,0]:+.4f}] y[{b[0,1]:+.4f},{b[1,1]:+.4f}] z[{b[0,2]:+.4f},{b[1,2]:+.4f}]")

    out = OUT + r"\blade_solid.stl"
    mesh.export(out)
    print(f"  exported {out}")
    if not mesh.is_watertight:
        print("  !! NOT watertight -- inspecting open edges")
        print(f"     open edges: {len(mesh.edges_unique) - (3*len(mesh.faces))//2 if False else 'n/a'}")
        broken = trimesh.repair.broken_faces(mesh)
        print(f"     broken_faces count: {len(broken)}")

if __name__ == "__main__":
    main()
