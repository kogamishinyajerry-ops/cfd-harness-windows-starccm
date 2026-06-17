# -*- coding: utf-8 -*-
"""Generate a rich set of geometry / data visualization figures for the report,
so a reader can SEE what is being reproduced and computed. Pure Python (numpy +
matplotlib + trimesh) from the real blade point cloud, reconstructed STLs and the
literature gold-standard — no solver needed. Writes PNGs to figs/."""
import os, json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm

ROOT = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans"
FIGS = ROOT + r"\figs"; os.makedirs(FIGS, exist_ok=True)
NPY = ROOT + r"\assets\deeplabs_rotor37_geometries_1.npy"
plt.rcParams.update({"font.size": 10, "axes.grid": True, "grid.alpha": .3,
                     "figure.facecolor": "white", "savefig.facecolor": "white",
                     "axes.titlesize": 12, "axes.unicode_minus": False,
                     "font.sans-serif": ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"],
                     "font.family": "sans-serif"})

s0 = np.asarray(np.load(NPY, mmap_mode="r")[0])      # (2,9,112,4) suction/pressure, 9 sec, 112 pts, xyz+lbl
NSEC = s0.shape[1]
def rad(p): return np.sqrt(p[..., 0]**2 + p[..., 1]**2)
def th(p):  return np.degrees(np.arctan2(p[..., 1], p[..., 0]))

# ---------- 1) blade 3D ----------
fig = plt.figure(figsize=(7.2, 6))
ax = fig.add_subplot(111, projection="3d")
allp = s0[..., :3].reshape(-1, 3)
r = np.sqrt(allp[:, 0]**2 + allp[:, 1]**2)
sc = ax.scatter(allp[:, 0], allp[:, 1], allp[:, 2], c=r, cmap="viridis", s=3)
ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z (axis) [m]")
ax.set_title("NASA Rotor 37 叶片 (重建样本0)\n按半径着色 · 36 叶片中的 1 片")
try: ax.set_box_aspect((np.ptp(allp[:,0]), np.ptp(allp[:,1]), np.ptp(allp[:,2])))
except Exception: pass
fig.colorbar(sc, ax=ax, shrink=.6, label="radius [m]")
ax.view_init(elev=22, azim=-60)
fig.savefig(FIGS + r"\fig_blade3d.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ---------- 2) 9 spanwise airfoil sections (blade-to-blade: z vs r*theta) ----------
fig, axs = plt.subplots(3, 3, figsize=(9.5, 8.4))
spanlbl = ["hub (0%)", "11%", "22%", "33%", "mid (50%)", "55%", "66%", "78%", "tip (100%)"]
for k in range(NSEC):
    ax = axs[k // 3][k % 3]
    suc = s0[0, k, :, :3]; pre = s0[1, k, :, :3]
    rm = rad(s0[:, k, :, :3]).mean()
    for surf, col, nm in [(suc, "#2e6b8b", "suction"), (pre, "#c0504d", "pressure")]:
        z = surf[:, 2]; s = np.radians(th(surf)) * rm
        ax.plot(z * 1000, s * 1000, col, lw=1.4)
    ax.set_title(f"sec {k}: {spanlbl[k]}  r≈{rm:.3f}m", fontsize=9)
    ax.set_aspect("equal"); ax.tick_params(labelsize=7)
    if k // 3 == 2: ax.set_xlabel("axial z [mm]", fontsize=8)
    if k % 3 == 0: ax.set_ylabel("pitchwise r·θ [mm]", fontsize=8)
fig.suptitle("Rotor 37 叶型沿叶高演化 (9 个展向截面, blade-to-blade 视图)\n蓝=吸力面 红=压力面 · 可见叶尖向轴向收口 (stagger 增大)", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.95])
fig.savefig(FIGS + r"\fig_sections.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ---------- 3) meridional flowpath (r-z) ----------
fig, ax = plt.subplots(figsize=(8.6, 4.6))
# hub = min r per axial bin of section0; shroud = max r per bin of section8
def envelope(sec, mode):
    p = s0[:, sec, :, :3].reshape(-1, 3); z = p[:, 2]; rr = rad(p)
    zb = np.linspace(z.min(), z.max(), 30); rc = []
    zc = .5 * (zb[:-1] + zb[1:])
    for i in range(len(zb) - 1):
        m = (z >= zb[i]) & (z <= zb[i + 1])
        rc.append((rr[m].min() if mode == "min" else rr[m].max()) if m.any() else np.nan)
    rc = np.array(rc); g = ~np.isnan(rc); return zc[g], rc[g]
zh, rh = envelope(0, "min"); zs, rs = envelope(NSEC - 1, "max")
zin, zout = -0.049, 0.153
ax.plot([zin, zh[0]] + list(zh) + [zout], [rh[0], rh[0]] + list(rh) + [rh[-1]], "k-", lw=2, label="hub 轮毂")
ax.plot([zin, zs[0]] + list(zs) + [zout], [rs[0] + 3.6e-4, rs[0] + 3.6e-4] + list(rs + 3.6e-4) + [rs[-1] + 3.6e-4], "k-", lw=2)
# blade region shade
allz = s0[..., 2]; ax.axvspan(allz.min(), allz.max(), color="#2e8b8b", alpha=.13, label="叶片轴向范围")
ax.text((allz.min()+allz.max())/2, (rh.mean()+rs.mean())/2, "BLADE\n(36×)", ha="center", va="center", fontsize=11, color="#1c4f4f", weight="bold")
ax.axvline(zin, ls="--", c="#2e8b8b"); ax.axvline(zout, ls="--", c="#c0504d")
ax.text(zin, rs.max()+3.6e-4, " 进口", color="#2e8b8b", fontsize=9, va="bottom")
ax.text(zout, rs.max()+3.6e-4, "出口 ", color="#c0504d", fontsize=9, va="bottom", ha="right")
ax.annotate("", xy=(0.10, 0.165), xytext=(0.0, 0.165), arrowprops=dict(arrowstyle="->", color="#555"))
ax.text(0.05, 0.168, "through-flow", fontsize=8, color="#555", ha="center")
ax.set_xlabel("axial z [m]"); ax.set_ylabel("radius r [m]"); ax.set_aspect("auto")
ax.set_title("Rotor 37 单通道子午流道 (r–z)\n轮毂上升、机匣近恒定的收缩环道 + 0.356mm 叶尖间隙")
ax.legend(loc="lower right", fontsize=8.5)
fig.savefig(FIGS + r"\fig_meridional.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ---------- 4) passage boundaries 3D ----------
import glob, trimesh
fig = plt.figure(figsize=(7.6, 6))
ax = fig.add_subplot(111, projection="3d")
colors = {"inlet": "#2ca02c", "outlet": "#d62728", "hub": "#8c564b", "shroud": "#7f7f7f",
          "blade": "#1f77b4", "per1": "#ff7f0e", "per2": "#e8c000"}
for f in sorted(glob.glob(ROOT + r"\geom\bc_*.stl")):
    nm = os.path.basename(f)[3:-4]
    try:
        m = trimesh.load(f); c = m.triangles_center
        st = max(1, len(c) // 1200)
        ax.scatter(c[::st, 0], c[::st, 1], c[::st, 2], s=2, c=colors.get(nm, "k"), label=nm)
    except Exception:
        pass
ax.set_xlabel("x [m]"); ax.set_ylabel("y [m]"); ax.set_zlabel("z [m]")
ax.set_title("单通道流域 — 7 个命名边界\n(求解器导入 + 自动建区)")
ax.legend(markerscale=3, fontsize=8, loc="upper left")
ax.view_init(elev=20, azim=-70)
fig.savefig(FIGS + r"\fig_passage3d.png", dpi=130, bbox_inches="tight"); plt.close(fig)

# ---------- 5) Suder validation characteristic map (target) ----------
fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.5))
# gold speed-line peak points (Suder1995 Table1/Fig4): mdot proxy by speed; show targets
spd = ["100%", "90%", "80%"]; mdot = [20.93, 19.0, 16.5]; PR = [2.056, 1.82, 1.55]; eta = [0.876, 0.866, 0.852]
a1.plot(mdot, PR, "o-", color="#2e8b8b", lw=2, ms=8)
for x, y, s in zip(mdot, PR, spd): a1.annotate(s, (x, y), textcoords="offset points", xytext=(6, 6), fontsize=9)
a1.scatter([20.93], [2.056], s=160, facecolors="none", edgecolors="#c0504d", lw=2, zorder=5, label="设计点 (peak η)")
a1.set_xlabel("corrected mass flow [kg/s]"); a1.set_ylabel("total pressure ratio PR"); a1.set_title("总压比–流量 (Suder 1995)")
a1.legend(fontsize=8); a1.grid(alpha=.3)
a2.plot(mdot, eta, "s-", color="#c0504d", lw=2, ms=8)
for x, y, s in zip(mdot, eta, spd): a2.annotate(s, (x, y), textcoords="offset points", xytext=(6, -12), fontsize=9)
a2.axhline(0.876, ls=":", c="#2e8b8b"); a2.scatter([20.93], [0.876], s=160, facecolors="none", edgecolors="#2e8b8b", lw=2, zorder=5)
a2.set_xlabel("corrected mass flow [kg/s]"); a2.set_ylabel("isentropic efficiency η"); a2.set_title("等熵效率–流量 (Suder 1995)")
a2.grid(alpha=.3)
fig.suptitle("验证目标：NASA Rotor 37 实验特性图 (Suder 1996 / Moore&Reid 1980) — RANS 复现需命中这些点", fontsize=12)
fig.tight_layout(rect=[0, 0, 1, 0.94])
fig.savefig(FIGS + r"\fig_suder_map.png", dpi=130, bbox_inches="tight"); plt.close(fig)

print("figures written to", FIGS)
for f in sorted(glob.glob(FIGS + r"\*.png")):
    print("  ", os.path.basename(f), os.path.getsize(f) // 1024, "KB")
