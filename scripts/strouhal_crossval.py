#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-validate the shedding Strouhal number via the LIFT history (FFT),
against the wake velocity-probe St, and extract real Cd_mean / Cl_rms.

Forces on 2402 R8 turned out to be READABLE once bound to the correctly
identified cylinder wall in a clean single-region sim (the old DEC-005
force-zero was a parts-binding bug, not a fundamental API limit). So:
  - lift(t)=Fx -> FFT/zero-crossing -> f_lift -> St_lift  (cross-checks St_vx)
  - drag(t)=Fz -> Cd_mean = mean(Fz)/Fref                  (real Cd!)
  - lift(t)    -> Cl_rms = std(Fx)/Fref, Cl_amp            (real Cl!)

Reads:  Cases/Results/lifthist_lift.csv / _drag.csv / _vx.csv
Writes: Cases/Results/strouhal_crossval.png, strouhal_crossval.json
"""
from __future__ import annotations
import csv
import json
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).parent))
import strouhal_analysis as sa   # reuse load_csv / zero_crossing_freq / fft_freq

D, U, RHO, L = 0.05, 0.5, 1.184, 0.02      # slab span L=0.02 m
FREF = 0.5 * RHO * U * U * D * L            # dynamic force scale
RE = U * D / 1.5e-5
RESULTS = Path(r"D:\StarCCM Codebuddy\Cases\Results")


def st_two_ways(t, x):
    fz, nc = sa.zero_crossing_freq(t, x)
    ff, _, _ = sa.fft_freq(t, x)
    return (fz, fz * D / U, nc), (ff, ff * D / U)


def main():
    lift_p = RESULTS / "lifthist_lift.csv"
    drag_p = RESULTS / "lifthist_drag.csv"
    vx_p = RESULTS / "lifthist_vx.csv"
    if not lift_p.exists():
        print(f"[crossval] MISSING {lift_p}", file=sys.stderr); sys.exit(2)

    tL, lift = sa.load_csv(lift_p)
    tD, drag = sa.load_csv(drag_p) if drag_p.exists() else (None, None)
    tV, vx = sa.load_csv(vx_p) if vx_p.exists() else (None, None)

    # St from lift
    (fzL, stzL, ncL), (ffL, stfL) = st_two_ways(tL, lift)
    # St from same-window velocity (cross-check)
    if vx is not None and len(vx) > 8:
        (fzV, stzV, ncV), (ffV, stfV) = st_two_ways(tV, vx)
    else:
        fzV = stzV = ncV = ffV = stfV = float("nan")

    # force coefficients
    cl = lift / FREF
    cl_mean = float(np.mean(cl))
    cl_rms = float(np.std(cl))                     # rms of fluctuation about mean
    cl_amp = float((np.max(cl) - np.min(cl)) / 2)
    if drag is not None:
        cd = drag / FREF
        cd_mean = float(np.mean(cd))
        cd_amp = float((np.max(cd) - np.min(cd)) / 2)
    else:
        cd = None; cd_mean = cd_amp = float("nan")

    # --- figure: lift + drag time series ---
    fig, axes = plt.subplots(2, 1, figsize=(8, 5.2), dpi=130, sharex=True)
    axes[0].plot(tL, cl, color="#6a1b9a", lw=1.2)
    axes[0].axhline(cl_mean, color="#999", ls="--", lw=0.8)
    axes[0].set_ylabel("Lift coeff  $C_L$")
    axes[0].set_title(f"Cylinder wall forces — $C_L$ oscillation -> St_lift={stzL:.3f} ({ncL} cycles)")
    axes[0].grid(alpha=0.25)
    if cd is not None:
        axes[1].plot(tD, cd, color="#00695c", lw=1.2)
        axes[1].axhline(cd_mean, color="#999", ls="--", lw=0.8,
                        label=f"$C_D$ mean = {cd_mean:.3f}")
        axes[1].legend(loc="upper right", fontsize=9)
    axes[1].set_ylabel("Drag coeff  $C_D$")
    axes[1].set_xlabel("Physical time  t  (s)")
    axes[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS / "strouhal_crossval.png")
    plt.close(fig)

    out = {
        "n_samples": int(len(tL)), "span_s": float(tL[-1] - tL[0]), "Re": round(RE, 1),
        "Fref_N": FREF,
        "St_lift_zc": round(stzL, 4), "St_lift_fft": round(stfL, 4),
        "f_lift_zc_hz": round(fzL, 4), "n_cycles_lift": int(ncL),
        "St_vx_zc": None if stzV != stzV else round(stzV, 4),
        "St_vx_fft": None if stfV != stfV else round(stfV, 4),
        "Cd_mean": round(cd_mean, 4), "Cd_amp": round(cd_amp, 4),
        "Cl_mean": round(cl_mean, 4), "Cl_rms": round(cl_rms, 4), "Cl_amp": round(cl_amp, 4),
        # literature anchors (subcritical Re~1700)
        "Cd_ref_sub": 1.1, "Cl_rms_ref_sub": 0.1, "St_ref_sub": 0.21,
    }
    (RESULTS / "strouhal_crossval.json").write_text(json.dumps(out, indent=2))
    print(f"[crossval] Re={RE:.0f} N={len(tL)} span={out['span_s']:.2f}s")
    print(f"[crossval] St_lift: zc={stzL:.4f} fft={stfL:.4f} ({ncL} cyc)  |  St_vx: zc={stzV:.4f} fft={stfV:.4f}")
    print(f"[crossval] Cd_mean={cd_mean:.3f} (±{cd_amp:.3f})  Cl_rms={cl_rms:.3f}  Cl_amp={cl_amp:.3f}")
    print(f"[crossval] agreement St_lift vs St_vx: {abs(stzL-stzV)/stzV*100:.1f}%" if stzV==stzV else "")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
