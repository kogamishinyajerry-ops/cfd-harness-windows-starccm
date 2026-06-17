"""Step 2: build a watertight single-passage fluid domain for Rotor 37 RANS.

Pipeline:
  1. Rebuild blade rings (sample 0) + a 'cutter' blade with root skirted ~2mm inward
     (clean hub intersection) and tip left short (0.356mm clearance handled by shroud).
  2. Derive contoured meridional walls r_hub(z), r_shroud(z) from blade root/tip envelopes,
     extended upstream/downstream at constant radius (inlet/outlet ducts).
  3. Build the annular wedge solid (one 10deg pitch) as a closed box of 6 patches.
  4. Boolean-subtract blade copies at k*pitch (k=-2..2) via manifold3d  -> fluid passage.
  5. Validate watertightness, classify boundary faces (inlet/outlet/hub/shroud/per1/per2/blade)
     and export each as a named STL for STAR-CCM+ import.

Axis = z (machine/rotation axis). point (z,r,theta) -> x=r cos th, y=r sin th, z=z.
"""
import os
import numpy as np
import trimesh
from trimesh import boolean

ASSETS = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\assets"
OUT = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\geom"
NPY = ASSETS + r"\deeplabs_rotor37_geometries_1.npy"

NCH = 112
NRING = 2 * NCH - 2          # 222
NBLADE = 36
PITCH = 2 * np.pi / NBLADE   # 10 deg
import os as _os
TIP_CLEAR = float(_os.environ.get("R37_TIP_CLEAR", "0.0"))  # 0 = flush (no-gap baseline); 0.000356 = real gap
TIP_SKIRT = 0.0006           # outward tip extension for clean flush cut when TIP_CLEAR==0
ROOT_SKIRT = 0.002           # 2 mm inward root extension for clean hub cut
INLET_EXT = 0.050            # m upstream of blade LE
OUTLET_EXT = 0.110           # m downstream of blade TE

# ---- mesh resolution of the bounding wedge (STAR-CCM+ re-meshes later) ----
M_AX = 140    # axial stations
T_TH = 48     # tangential
R_RAD = 40    # radial (on inlet/outlet/periodic faces)

def ring_of(s0, k):
    suction = s0[0, k, :, :3]
    pressure = s0[1, k, :, :3]
    return np.vstack([suction, pressure[1:NCH-1]])

def pf_ringidx(i):
    if i == 0:
        return 0
    if i == NCH - 1:
        return NCH - 1
    return NRING - i

def blade_mesh(rings):
    """Build watertight blade from a (nsec,NRING,3) ring stack."""
    nsec = rings.shape[0]
    verts = rings.reshape(-1, 3)
    N = NRING
    def vid(k, i): return k * N + (i % N)
    faces = []
    for k in range(nsec - 1):
        for i in range(N):
            a, b = vid(k, i), vid(k, i + 1)
            c, d = vid(k + 1, i + 1), vid(k + 1, i)
            faces += [[a, b, c], [a, c, d]]
    def cap(k):
        cf = []
        for i in range(NCH - 1):
            s_a, s_b = vid(k, i), vid(k, i + 1)
            p_a, p_b = vid(k, pf_ringidx(i)), vid(k, pf_ringidx(i + 1))
            cf += [[s_a, s_b, p_b], [s_a, p_b, p_a]]
        return cf
    faces += cap(0) + cap(nsec - 1)
    m = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=True)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices(); m.fix_normals()
    return m

def radial_shift(ring, dr):
    """Shift a ring radially by dr (about z axis), keep theta and z."""
    x, y, z = ring[:, 0], ring[:, 1], ring[:, 2]
    r = np.sqrt(x**2 + y**2)
    th = np.arctan2(y, x)
    rn = r + dr
    return np.column_stack([rn * np.cos(th), rn * np.sin(th), z])

def rotate_z(mesh, ang):
    m = mesh.copy()
    R = trimesh.transformations.rotation_matrix(ang, [0, 0, 1])
    m.apply_transform(R)
    return m

def meridional_walls(s0):
    """r_hub(z), r_shroud(z) as np.interp tables over full axial extent."""
    root = ring_of(s0, 0)
    tip = ring_of(s0, s0.shape[1] - 1)
    def envelope(ring, mode):
        z = ring[:, 2]; r = np.sqrt(ring[:, 0]**2 + ring[:, 1]**2)
        zb = np.linspace(z.min(), z.max(), 40)
        rb = np.empty_like(zb)
        for i in range(len(zb) - 1):
            sel = (z >= zb[i]) & (z <= zb[i + 1])
            if sel.any():
                rb[i] = r[sel].min() if mode == "min" else r[sel].max()
            else:
                rb[i] = np.nan
        rb[-1] = r[z >= zb[-2]].min() if mode == "min" else r[z >= zb[-2]].max()
        good = ~np.isnan(rb)
        zc = 0.5 * (zb[:-1] + zb[1:]); zc = np.append(zc, zb[-1])
        return zc[good], rb[good]
    zh, rh = envelope(root, "min")
    zs, rs = envelope(tip, "max")
    z_le = min(zh.min(), zs.min()); z_te = max(zh.max(), zs.max())
    z_in = z_le - INLET_EXT; z_out = z_te + OUTLET_EXT
    # extend constant up/downstream
    zh = np.concatenate([[z_in], zh, [z_out]]); rh = np.concatenate([[rh[0]], rh, [rh[-1]]])
    zs = np.concatenate([[z_in], zs, [z_out]]); rs = np.concatenate([[rs[0]], rs, [rs[-1]]]) + TIP_CLEAR
    # sort & dedup
    def clean(zz, rr):
        o = np.argsort(zz); zz, rr = zz[o], rr[o]
        u, idx = np.unique(zz, return_index=True)
        return zz[idx], rr[idx]
    zh, rh = clean(zh, rh); zs, rs = clean(zs, rs)
    r_hub = lambda z: np.interp(z, zh, rh)
    r_shroud = lambda z: np.interp(z, zs, rs)
    return r_hub, r_shroud, z_in, z_out

def build_wedge(r_hub, r_shroud, z_in, z_out, th0):
    zc = np.linspace(z_in, z_out, M_AX)
    th = np.linspace(th0, th0 + PITCH, T_TH)
    u = np.linspace(0, 1, R_RAD)
    rh = r_hub(zc); rs = r_shroud(zc)
    def P(r, th_, z): return np.array([r*np.cos(th_), r*np.sin(th_), z])
    verts = []; faces = []
    vmap = {}
    def add(key, p):
        if key in vmap: return vmap[key]
        vmap[key] = len(verts); verts.append(p); return vmap[key]
    def quad(a, b, c, d): faces.append([a, b, c]); faces.append([a, c, d])
    # hub (i over axial, j over theta)
    for i in range(M_AX - 1):
        for j in range(T_TH - 1):
            a = add(("h", i, j),   P(rh[i],   th[j],   zc[i]))
            b = add(("h", i+1, j), P(rh[i+1], th[j],   zc[i+1]))
            c = add(("h", i+1, j+1),P(rh[i+1], th[j+1], zc[i+1]))
            d = add(("h", i, j+1), P(rh[i],   th[j+1], zc[i]))
            quad(a, b, c, d)
    # shroud
    for i in range(M_AX - 1):
        for j in range(T_TH - 1):
            a = add(("s", i, j),    P(rs[i],   th[j],   zc[i]))
            b = add(("s", i, j+1),  P(rs[i],   th[j+1], zc[i]))
            c = add(("s", i+1, j+1),P(rs[i+1], th[j+1], zc[i+1]))
            d = add(("s", i+1, j),  P(rs[i+1], th[j],   zc[i+1]))
            quad(a, b, c, d)
    def rad_face(i, key):
        z = zc[i]; rL = r_hub(z); rU = r_shroud(z)
        for jt in range(T_TH - 1):
            for ju in range(R_RAD - 1):
                def rr(uu): return rL + uu * (rU - rL)
                a = add((key, i, jt, ju),     P(rr(u[ju]),   th[jt],   z))
                b = add((key, i, jt, ju+1),   P(rr(u[ju+1]), th[jt],   z))
                c = add((key, i, jt+1, ju+1), P(rr(u[ju+1]), th[jt+1], z))
                d = add((key, i, jt+1, ju),   P(rr(u[ju]),   th[jt+1], z))
                quad(a, b, c, d)
    rad_face(0, "in")
    rad_face(M_AX - 1, "out")
    def per_face(jt_idx, key):
        th_ = th[jt_idx]
        for i in range(M_AX - 1):
            rL0, rU0 = r_hub(zc[i]), r_shroud(zc[i])
            rL1, rU1 = r_hub(zc[i+1]), r_shroud(zc[i+1])
            for ju in range(R_RAD - 1):
                a = add((key, i, ju),     P(rL0 + u[ju]   *(rU0-rL0), th_, zc[i]))
                b = add((key, i, ju+1),   P(rL0 + u[ju+1] *(rU0-rL0), th_, zc[i]))
                c = add((key, i+1, ju+1), P(rL1 + u[ju+1] *(rU1-rL1), th_, zc[i+1]))
                d = add((key, i+1, ju),   P(rL1 + u[ju]   *(rU1-rL1), th_, zc[i+1]))
                quad(a, b, c, d)
    per_face(0, "p0")
    per_face(T_TH - 1, "p1")
    m = trimesh.Trimesh(vertices=np.array(verts), faces=np.array(faces), process=True)
    m.merge_vertices(); m.update_faces(m.nondegenerate_faces())
    m.remove_unreferenced_vertices(); m.fix_normals()
    return m

def main():
    os.makedirs(OUT, exist_ok=True)
    arr = np.load(NPY, mmap_mode="r")
    s0 = np.asarray(arr[0]); nsec = s0.shape[1]
    rings = np.array([ring_of(s0, k) for k in range(nsec)])

    blade = blade_mesh(rings)
    # cutter: root ring skirted 2mm inward (clean hub cut); if no tip gap, also extend
    # the tip ring outward so the blade pokes through the shroud -> flush (no-gap) cut.
    skirt = radial_shift(rings[0], -ROOT_SKIRT)[None, ...]
    if TIP_CLEAR <= 0.0:
        tipskirt = radial_shift(rings[-1], +TIP_SKIRT)[None, ...]
        cutter_rings = np.concatenate([skirt, rings, tipskirt], axis=0)
        print("NO-GAP build: blade tip flush to shroud (tip skirt +%.4g m)" % TIP_SKIRT)
    else:
        cutter_rings = np.concatenate([skirt, rings], axis=0)
        print("GAP build: tip clearance %.4g m" % TIP_CLEAR)
    cutter = blade_mesh(cutter_rings)
    print(f"blade watertight={blade.is_watertight} vol={blade.volume:.3e}; "
          f"cutter watertight={cutter.is_watertight} vol={cutter.volume:.3e}")

    r_hub, r_shroud, z_in, z_out = meridional_walls(s0)
    th_blade = np.arctan2(rings[..., 1], rings[..., 0])
    th_c = th_blade.mean()
    th0 = th_c - PITCH / 2.0
    print(f"axial domain z=[{z_in:.4f},{z_out:.4f}]  hub r@in={r_hub(z_in):.4f} shroud r@in={r_shroud(z_in):.4f}")
    print(f"blade theta center={np.degrees(th_c):.2f} deg, wedge th=[{np.degrees(th0):.2f},{np.degrees(th0+PITCH):.2f}]")

    wedge = build_wedge(r_hub, r_shroud, z_in, z_out, th0)
    print(f"wedge watertight={wedge.is_watertight} vol={wedge.volume:.4e} faces={len(wedge.faces)}")

    # subtract blade copies at k*pitch
    cutters = [rotate_z(cutter, k * PITCH) for k in (-2, -1, 0, 1, 2)]
    blades_union = boolean.union(cutters, engine="manifold")
    fluid = boolean.difference([wedge, blades_union], engine="manifold")
    if isinstance(fluid, list):
        fluid = max(fluid, key=lambda m: m.volume)
    fluid.merge_vertices(); fluid.fix_normals()
    print(f"\nFLUID: watertight={fluid.is_watertight} vol={fluid.volume:.4e} m^3 "
          f"verts={len(fluid.vertices)} faces={len(fluid.faces)} euler={fluid.euler_number}")

    fluid.export(OUT + r"\fluid_passage.stl")
    blade.export(OUT + r"\blade_solid.stl")

    # ---- classify boundary faces ----
    fc = fluid.triangles_center
    x, y, z = fc[:, 0], fc[:, 1], fc[:, 2]
    r = np.sqrt(x**2 + y**2); th = np.arctan2(y, x)
    rh = r_hub(z); rs = r_shroud(z)
    label = np.full(len(fc), "blade", dtype=object)
    label[np.abs(z - z_in) < 5e-4] = "inlet"
    label[np.abs(z - z_out) < 5e-4] = "outlet"
    rem = np.isin(label, ["blade"])
    label[rem & (np.abs(th - th0) < 1.5e-3)] = "per1"
    rem = np.isin(label, ["blade"])
    label[rem & (np.abs(th - (th0 + PITCH)) < 1.5e-3)] = "per2"
    rem = np.isin(label, ["blade"])
    label[rem & (np.abs(r - rh) < 1.2e-3)] = "hub"
    rem = np.isin(label, ["blade"])
    label[rem & (np.abs(r - rs) < 1.2e-3)] = "shroud"

    groups = {}
    for name in ["inlet", "outlet", "hub", "shroud", "per1", "per2", "blade"]:
        idx = np.where(label == name)[0]
        groups[name] = len(idx)
        if len(idx):
            sub = fluid.submesh([idx], append=True)
            sub.export(OUT + f"\\bc_{name}.stl")
    print("boundary face counts:", groups)
    # periodic consistency check
    print(f"per1 vs per2 face balance: {groups['per1']} / {groups['per2']} (should be ~equal)")

if __name__ == "__main__":
    main()
