#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Measure the Karman shedding Strouhal number from a wake velocity time series.

Reads the lateral-velocity monitor CSV exported by VortexStrouhal.java
(Cases/Results/strouhal_vx.csv), estimates the shedding frequency two
independent ways (FFT peak + zero-crossing period), and computes
St = f*D/U. This BYPASSES the DEC-005 force-read dead-end: velocity-field
probes read real data, unlike the force reports (sentinel zeros).

Outputs:
  - Cases/Results/strouhal_timeseries.png
  - Cases/Results/strouhal_spectrum.png
  - Cases/Results/strouhal_result.json   (consumed by vortex_report.py)
  - prints a one-line summary
"""
from __future__ import annotations
import csv
import json
import math
import sys
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# --- case constants ---
D = 0.05      # cylinder diameter [m]
U = 0.5       # inlet / freestream velocity [m/s]
NU = 1.5e-5   # kinematic viscosity [m^2/s] (Re = U*D/nu)
RE = U * D / NU

CB = Path(r"D:\StarCCM Codebuddy")
RESULTS = CB / "Cases" / "Results"


def load_csv(path: Path):
    """Return (t, v) float arrays from a STAR-CCM+ monitor export.

    Handles the quoted 2-column header
    ``"Physical Time (s)","St_Vx Monitor (m/s)"`` and the plain
    ``time_s,vx`` fallback dump.
    """
    t, v = [], []
    with open(path, newline="") as f:
        rdr = csv.reader(f)
        rows = list(rdr)
    start = 0
    if rows and not _is_float(rows[0][0]):
        start = 1  # skip header
    for r in rows[start:]:
        if len(r) < 2:
            continue
        try:
            t.append(float(r[0])); v.append(float(r[1]))
        except ValueError:
            continue
    return np.asarray(t), np.asarray(v)


def _is_float(s: str) -> bool:
    try:
        float(s); return True
    except ValueError:
        return False


def zero_crossing_freq(t, x):
    """Shedding frequency from spacing of rising edges, via a Schmitt trigger.

    A plain zero-crossing counter mis-fires on noise jitter near the zero
    level (each true crossing can trigger several times). A Schmitt trigger
    with hysteresis ±h only registers a rising edge after the signal has
    first dropped below -h, so noise can't double-count. Linear-detrend
    first to remove any slow wake drift. Returns (f, n_cycles) or (nan, 0).
    """
    from scipy.signal import detrend
    x = detrend(np.asarray(x, float), type="linear")
    # light moving-average smooth (~5 samples) to suppress noise jitter at the
    # zero level without distorting the ~100-sample/cycle shedding signal
    if len(x) >= 7:
        k = 5
        x = np.convolve(x, np.ones(k) / k, mode="same")
    h = 0.3 * np.std(x)                       # hysteresis band
    if h <= 0:
        return float("nan"), 0
    state = -1 if x[0] < 0 else 1             # start armed-low / high
    rises = []
    for i in range(1, len(x)):
        if state < 0 and x[i] > h:            # low -> high : a rising edge
            # interpolate the zero up-crossing time just before this point
            j = i
            while j > 0 and x[j - 1] > 0:
                j -= 1
            if j >= 1 and x[j] != x[j - 1]:
                frac = -x[j - 1] / (x[j] - x[j - 1])
                rises.append(t[j - 1] + frac * (t[j] - t[j - 1]))
            else:
                rises.append(t[i])
            state = 1
        elif state > 0 and x[i] < -h:         # high -> low : re-arm
            state = -1
    if len(rises) < 2:
        return float("nan"), 0
    periods = np.diff(rises)
    return 1.0 / np.mean(periods), len(rises) - 1


def fft_freq(t, x):
    """Dominant non-DC frequency via rFFT on the (uniform) series.

    Returns (f_peak, freqs, amp).
    """
    x = x - np.mean(x)
    n = len(x)
    dt = np.median(np.diff(t))
    # Hann window to reduce leakage with few cycles
    w = np.hanning(n)
    X = np.fft.rfft(x * w)
    freqs = np.fft.rfftfreq(n, d=dt)
    amp = np.abs(X)
    if len(amp) > 1:
        k = 1 + int(np.argmax(amp[1:]))      # skip DC
        f_peak = freqs[k]
        # parabolic (quadratic) interpolation around the peak bin for
        # sub-bin frequency resolution (coarse Δf with few cycles otherwise)
        if 1 <= k < len(amp) - 1:
            a, b, c = amp[k - 1], amp[k], amp[k + 1]
            denom = a - 2 * b + c
            if denom != 0:
                delta = 0.5 * (a - c) / denom    # in [-0.5, 0.5] bins
                f_peak = (k + delta) * (freqs[1] - freqs[0])
    else:
        f_peak = float("nan")
    return f_peak, freqs, amp


def main():
    csv_path = RESULTS / "strouhal_vx.csv"
    if not csv_path.exists():
        print(f"[strouhal] MISSING {csv_path}", file=sys.stderr)
        sys.exit(2)
    t, v = load_csv(csv_path)
    if len(t) < 8:
        print(f"[strouhal] too few samples: {len(t)}", file=sys.stderr)
        sys.exit(3)

    f_zc, n_cyc = zero_crossing_freq(t, v)
    f_fft, freqs, amp = fft_freq(t, v)
    st_zc = f_zc * D / U if f_zc == f_zc else float("nan")
    st_fft = f_fft * D / U if f_fft == f_fft else float("nan")
    span = float(t[-1] - t[0])
    dt = float(np.median(np.diff(t)))

    # --- figure 1: time series ---
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=130)
    ax.plot(t, v, color="#1565c0", lw=1.2)
    ax.axhline(np.mean(v), color="#999", lw=0.8, ls="--")
    ax.set_xlabel("Physical time  t  (s)")
    ax.set_ylabel("Lateral velocity  $u_x$  (m/s)")
    ax.set_title(f"Wake probe (0,0,0.10) lateral velocity — {n_cyc} shedding cycles over {span:.2f}s")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS / "strouhal_timeseries.png")
    plt.close(fig)

    # --- figure 2: spectrum ---
    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=130)
    ax.plot(freqs, amp, color="#c62828", lw=1.2)
    if f_fft == f_fft:
        ax.axvline(f_fft, color="#2e7d32", lw=1.0, ls="--",
                   label=f"peak f = {f_fft:.3f} Hz → St = {st_fft:.3f}")
        ax.legend(loc="upper right", fontsize=9)
    ax.set_xlim(0, max(8.0, (f_fft if f_fft == f_fft else 4) * 3))
    ax.set_xlabel("Frequency  f  (Hz)")
    ax.set_ylabel("Amplitude (windowed)")
    ax.set_title("Lateral-velocity spectrum")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(RESULTS / "strouhal_spectrum.png")
    plt.close(fig)

    result = {
        "n_samples": int(len(t)),
        "dt_s": dt,
        "span_s": span,
        "n_cycles_zc": int(n_cyc),
        "f_zc_hz": None if f_zc != f_zc else round(f_zc, 4),
        "f_fft_hz": None if f_fft != f_fft else round(f_fft, 4),
        "St_zc": None if st_zc != st_zc else round(st_zc, 4),
        "St_fft": None if st_fft != st_fft else round(st_fft, 4),
        "D_m": D, "U_ms": U, "nu": NU, "Re": round(RE, 1),
        # literature anchors for the subcritical regime
        "St_ref_subcritical": 0.21,   # Norberg ~Re 1000-2000
        "St_ref_williamson200": 0.198,
    }
    (RESULTS / "strouhal_result.json").write_text(json.dumps(result, indent=2))
    print(f"[strouhal] Re={RE:.0f}  N={len(t)}  span={span:.2f}s  cycles={n_cyc}")
    print(f"[strouhal] f_zc={f_zc:.4f}Hz St_zc={st_zc:.4f} | f_fft={f_fft:.4f}Hz St_fft={st_fft:.4f}")
    print(f"[strouhal] ref subcritical St~0.21 (Re~1700, Norberg); Williamson Re200 St=0.198")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
