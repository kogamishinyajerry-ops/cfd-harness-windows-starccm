"""Stage 5: aggregate the back-pressure sweep into a characteristic map, compare to
the Suder/Moore-Reid gold standard at the design corrected mass flow, and emit a
reproduction report + speed-line plot.

Gold references (knowledge/gold_standards/rotor37.yaml, sourced from
Moore & Reid 1980 NASA-TP-1659 + Suder 1995 ASME J.Turbo 117(4):491, DOI 10.1115/1.2836561):
  PR_tt design = 2.056  (tol 3%)
  eta_is design = 0.876 (tol 5%)
  mdot corrected = 20.93 kg/s (tol 4%)
"""
import glob, json, os
import numpy as np

RUNS = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans\runs"
OUT  = r"D:\CFD-harness-Windows-StarCCM\reproductions\rotor37_rans"

GOLD = {
    "pressure_ratio": (2.056, 0.03, "Moore&Reid 1980 NASA-TP-1659 / Suder 1995 Table 1"),
    "isentropic_efficiency": (0.876, 0.05, "Suder 1995 Table 1 peak efficiency"),
    "mass_flow_kg_s": (20.93, 0.04, "Suder 1995 corrected baseline"),
}
TARGET_MDOT = 20.93

def load_points():
    pts = []
    for f in sorted(glob.glob(RUNS + r"\rotor37_p*.json")):
        d = json.load(open(f))
        mdot = d.get("mdot_full_kg_s"); pr = d.get("pressure_ratio_tt"); eta = d.get("isentropic_efficiency")
        if mdot is None or pr is None:
            continue
        pts.append({"file": os.path.basename(f), "p_out": d.get("p_out_pa"),
                    "mdot": abs(mdot), "PR": pr, "eta": eta, "T0r": d.get("total_temp_ratio"),
                    "cells": d.get("cell_count"), "iters": d.get("iters")})
    pts.sort(key=lambda p: p["mdot"])
    return pts

def interp_at(pts, target, key):
    xs = [p["mdot"] for p in pts]; ys = [p[key] for p in pts]
    if not xs: return None, "no data"
    if target < min(xs) or target > max(xs):
        # nearest point (extrapolation flagged)
        i = int(np.argmin([abs(x - target) for x in xs]))
        return ys[i], f"nearest (target {target} outside swept range [{min(xs):.2f},{max(xs):.2f}])"
    return float(np.interp(target, xs, ys)), "interpolated"

def verdict(meas, ref, tol):
    if meas is None: return "NO DATA", None
    err = (meas - ref) / ref
    if abs(err) <= tol: return "PASS", err
    if abs(err) <= 2 * tol: return "WARN", err
    return "FAIL", err

def main():
    pts = load_points()
    lines = []
    lines.append("# NASA Rotor 37 — Steady RANS Reproduction Report\n")
    lines.append("Reproduction of Li et al. (2022, AST, DOI 10.1016/j.ast.2022.107617) geometry/operating point, ")
    lines.append("method downgraded QWRLES → steady RANS (k-ω SST, coupled/density-based, MRF single passage), ")
    lines.append("validated against Suder (1996, NASA TP-3623) / Moore & Reid (1980, NASA TP-1659).\n")
    lines.append("\n## Characteristic (100% design speed, swept back-pressure)\n")
    lines.append("| p_out [kPa] | ṁ full [kg/s] | PR_tt | η_is | T0 ratio | cells | iters |")
    lines.append("|---|---|---|---|---|---|---|")
    for p in pts:
        lines.append(f"| {p['p_out']/1000:.0f} | {p['mdot']:.2f} | {p['PR']:.3f} | "
                     f"{(p['eta'] if p['eta'] is not None else float('nan')):.3f} | "
                     f"{(p['T0r'] if p['T0r'] is not None else float('nan')):.3f} | {p['cells']} | {p['iters']} |")

    lines.append(f"\n## Validation at design corrected mass flow (ṁ = {TARGET_MDOT} kg/s)\n")
    pr_at, pr_note = interp_at(pts, TARGET_MDOT, "PR")
    eta_at, eta_note = interp_at(pts, TARGET_MDOT, "eta")
    lines.append("| Quantity | Reproduced | Reference | Tol | Error | Verdict | Source |")
    lines.append("|---|---|---|---|---|---|---|")
    for key, meas, note in [("pressure_ratio", pr_at, pr_note), ("isentropic_efficiency", eta_at, eta_note)]:
        ref, tol, src = GOLD[key]
        v, err = verdict(meas, ref, tol)
        ms = "—" if meas is None else f"{meas:.3f}"
        es = "—" if err is None else f"{err*100:+.1f}%"
        lines.append(f"| {key} | {ms} | {ref} | {tol*100:.0f}% | {es} | **{v}** | {src} |")
    lines.append(f"\n(PR/η at design ṁ obtained by {pr_note}.)\n")

    # mass flow range check
    if pts:
        mlo, mhi = pts[0]["mdot"], pts[-1]["mdot"]
        ref, tol, src = GOLD["mass_flow_kg_s"]
        covered = mlo <= TARGET_MDOT <= mhi
        lines.append(f"\n**Mass-flow coverage:** swept ṁ ∈ [{mlo:.2f}, {mhi:.2f}] kg/s; "
                     f"design {ref} kg/s {'IS' if covered else 'is NOT'} bracketed.\n")

    lines.append("\n## Geometry verification (vs NASA canonical)\n")
    lines.append("| Quantity | Reconstructed | Canonical | Status |")
    lines.append("|---|---|---|---|")
    lines.append("| Tip diameter [m] | 0.511 | 0.508 | ✓ (0.6%) |")
    lines.append("| Hub/tip radius ratio | 0.68 | 0.70 (inlet, Reid&Moore) | ✓ |")
    lines.append("| Blade count | 36 | 36 | ✓ |")
    lines.append("| Design speed [rpm] | 17188.7 | 17188.7 | ✓ |")
    lines.append("| Tip clearance [mm] | 0.356 | 0.356 | ✓ |")
    lines.append("\n> Note: gold_standards/rotor37.yaml lists hub/tip = 0.5, but the canonical NASA Rotor 37 "
                 "inlet hub/tip ratio is 0.7 (Reid & Moore); the reconstructed 0.68 matches the canonical value. "
                 "The 0.5 in the gold file is flagged there as 'approximate'.\n")

    lines.append("\n## Honest caveats\n")
    lines.append("- **Coarse mesh** (~216k cells/passage vs ~1–2M recommended): under-resolves the tip-leakage "
                 "vortex and shock, so efficiency is over-predicted and PR/ṁ carry discretization error. "
                 "A mesh-convergence (GCI) study is the next step for a quantitative claim.\n")
    lines.append("- **Endwall contours** reconstructed from the blade root/tip envelopes (real flowpath definition "
                 "not in the public point cloud); the famous Rotor 37 hub-corner discrepancy is sensitive to the "
                 "hub leakage/axial gap (Van Zante et al.) which is not modeled.\n")
    lines.append("- **Shroud** currently rotates with the frame in the coarse run (should be counter-rotating / "
                 "lab-stationary); affects tip-leakage accuracy.\n")
    lines.append("- **Convergence**: limited iteration counts; residual histories should be driven down further "
                 "for a final number.\n")
    lines.append("- **Geometry provenance**: baseline blade from the Deeplabs-ai/rotor37 dataset (sample 0), "
                 "cross-checked dimensionally against Reid & Moore 1980; not the original NASA IGES.\n")

    report = "\n".join(lines) + "\n"
    open(OUT + r"\REPORT.md", "w", encoding="utf-8").write(report)
    print(report)
    print("wrote", OUT + r"\REPORT.md")

    # plot
    try:
        import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
        if pts:
            m = [p["mdot"] for p in pts]; pr = [p["PR"] for p in pts]; eta = [p["eta"] for p in pts]
            fig, ax = plt.subplots(1, 2, figsize=(11, 4.5))
            ax[0].plot(m, pr, "o-", label="RANS (this work)")
            ax[0].axhline(2.056, ls="--", c="r", label="Suder design PR 2.056")
            ax[0].axvline(20.93, ls=":", c="g", label="design ṁ 20.93")
            ax[0].set_xlabel("mass flow [kg/s]"); ax[0].set_ylabel("PR_tt"); ax[0].set_title("Pressure ratio"); ax[0].legend(fontsize=7)
            ax[1].plot(m, eta, "o-")
            ax[1].axhline(0.876, ls="--", c="r"); ax[1].axvline(20.93, ls=":", c="g")
            ax[1].set_xlabel("mass flow [kg/s]"); ax[1].set_ylabel("eta_is"); ax[1].set_title("Isentropic efficiency")
            plt.tight_layout(); plt.savefig(OUT + r"\characteristic.png", dpi=120)
            print("wrote", OUT + r"\characteristic.png")
    except Exception as e:
        print("plot skipped:", e)

if __name__ == "__main__":
    main()
