"""Inspect the acquired Rotor 37 blade point cloud (sample 0 = baseline) and
cross-check it against known NASA Rotor 37 design dimensions before we build a mesh.

Reference (Reid & Moore 1978 / Suder; rotor37.yaml gold standard):
  tip diameter ~0.508 m  -> tip radius ~0.254 m
  inlet hub-tip radius ratio ~0.70
  blade count = 36  -> pitch = 10 deg
"""
import sys
import numpy as np

NPY = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\assets\deeplabs_rotor37_geometries_1.npy"

def main():
    arr = np.load(NPY, mmap_mode="r")
    print(f"file shape={arr.shape} dtype={arr.dtype}")
    s0 = np.asarray(arr[0])  # (2, 9, 112, 4)
    print(f"sample0 shape={s0.shape}")
    xyz = s0[..., :3].reshape(-1, 3)  # all points, (N,3)
    print(f"points={xyz.shape[0]} finite={np.isfinite(xyz).all()}")
    for i, ax in enumerate("xyz"):
        print(f"  {ax}: min={xyz[:,i].min():+.5f}  max={xyz[:,i].max():+.5f}  span={np.ptp(xyz[:,i]):.5f}")

    # Determine rotation axis: the axis along which the blade is "long" (axial),
    # vs the two that form the radius (~0.17-0.255). Test each candidate axis.
    print("\nRadius test per candidate rotation axis (expect hub~0.171, tip~0.254):")
    for axis in range(3):
        other = [j for j in range(3) if j != axis]
        r = np.sqrt(xyz[:, other[0]]**2 + xyz[:, other[1]]**2)
        print(f"  axis={'xyz'[axis]}: r_min={r.min():.4f} r_max={r.max():.4f} "
              f"(hub/tip ratio={r.min()/r.max():.3f})  axial_span={np.ptp(xyz[:,axis]):.4f}")

    # Pick the axis whose radius range best matches 0.171..0.255
    best, bestscore = None, 1e9
    for axis in range(3):
        other = [j for j in range(3) if j != axis]
        r = np.sqrt(xyz[:, other[0]]**2 + xyz[:, other[1]]**2)
        score = abs(r.max() - 0.254) + abs(r.min()/r.max() - 0.70)
        if score < bestscore:
            best, bestscore = axis, score
    other = [j for j in range(3) if j != best]
    r = np.sqrt(xyz[:, other[0]]**2 + xyz[:, other[1]]**2)
    theta = np.degrees(np.arctan2(xyz[:, other[1]], xyz[:, other[0]]))
    print(f"\n==> rotation axis = '{'xyz'[best]}'")
    print(f"    tip radius  = {r.max():.4f} m   (ref 0.254)")
    print(f"    hub radius  = {r.min():.4f} m   (ref ~0.178)")
    print(f"    hub/tip     = {r.min()/r.max():.3f}  (ref ~0.70)")
    print(f"    axial chord ~ {np.ptp(xyz[:,best]):.4f} m")
    print(f"    angular spread of one blade = {np.ptp(theta):.2f} deg  (blade pitch=10 deg)")

    # Spanwise sections: section index varies along radius?
    print("\nPer-section radius (9 sections, hub->tip expected monotonic):")
    for k in range(s0.shape[1]):
        sec = s0[:, k, :, :3].reshape(-1, 3)
        rr = np.sqrt(sec[:, other[0]]**2 + sec[:, other[1]]**2)
        print(f"  section {k}: r_mean={rr.mean():.4f}  r=[{rr.min():.4f},{rr.max():.4f}]")

if __name__ == "__main__":
    main()
