"""Freeze geometry/operating metadata for the macro + report, and render a sanity view."""
import glob, os, json
import numpy as np
import trimesh

GEOM = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\geom"
RPM = 17188.7
omega = RPM * 2 * np.pi / 60.0

fluid = trimesh.load(GEOM + r"\fluid_passage.stl")
meta = {
    "case": "nasa_rotor37_single_passage_rans",
    "geometry_source": "Deeplabs-ai/rotor37 sample 0 (baseline NASA Rotor 37), verified vs Reid&Moore 1978",
    "rotation_axis": "z",
    "blade_count": 36,
    "pitch_deg": 10.0,
    "rpm": RPM,
    "omega_rad_s": round(omega, 3),
    "tip_clearance_m": 0.000356,
    "fluid_volume_m3": float(fluid.volume),
    "z_inlet_m": float(fluid.bounds[0, 2]),
    "z_outlet_m": float(fluid.bounds[1, 2]),
    "inlet_total_pressure_pa": 101325.0,
    "inlet_total_temperature_k": 288.15,
    "outlet_static_pressure_pa_initial": 115000.0,
    "design": {"pressure_ratio": 2.106, "adiabatic_efficiency": 0.876,
               "mass_flow_kg_s": 20.19, "choke_mass_flow_kg_s": 20.93},
    "boundaries": ["inlet", "outlet", "hub", "shroud", "blade", "per1", "per2"],
    "wall_roles": {"hub": "rotating_with_frame", "blade": "rotating_with_frame",
                   "shroud": "counter_rotating_absolute_stationary"},
}
with open(GEOM + r"\rotor37_meta.json", "w") as f:
    json.dump(meta, f, indent=2)
print("meta written:", json.dumps(meta, indent=2))

# --- sanity view ---
try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    colors = {"inlet":"tab:green","outlet":"tab:red","hub":"tab:brown","shroud":"tab:gray",
              "blade":"tab:blue","per1":"tab:orange","per2":"gold"}
    fig = plt.figure(figsize=(12,5))
    ax = fig.add_subplot(121, projection="3d")
    ax2 = fig.add_subplot(122)
    for f in sorted(glob.glob(GEOM + r"\bc_*.stl")):
        name = os.path.basename(f)[3:-4]
        m = trimesh.load(f); c = m.triangles_center
        step = max(1, len(c)//1500)
        ax.scatter(c[::step,0], c[::step,1], c[::step,2], s=2, c=colors.get(name,"k"), label=name)
        r = np.sqrt(c[:,0]**2+c[:,1]**2)
        ax2.scatter(c[::step,2], r[::step], s=2, c=colors.get(name,"k"), label=name)
    ax.set_title("Rotor37 single passage (3D)"); ax.legend(markerscale=3, fontsize=7)
    ax2.set_title("Meridional (z vs r)"); ax2.set_xlabel("z [m]"); ax2.set_ylabel("r [m]")
    ax2.legend(markerscale=3, fontsize=7)
    plt.tight_layout(); plt.savefig(GEOM + r"\passage_view.png", dpi=110)
    print("view saved:", GEOM + r"\passage_view.png")
except Exception as e:
    print("view skipped:", e)
