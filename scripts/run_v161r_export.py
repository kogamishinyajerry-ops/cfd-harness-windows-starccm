#!/usr/bin/env python
"""Run v161R sim through STAR-CCM+ with a fresh "export PNG" macro.

Loads D:\\StarCCM Codebuddy\\Cases\\cyl_vortex_v161R_v26_solved.sim
(a real STAR-CCM+ 19.02.009 simulation from 2026-06-05) and runs
PatchV161R_ExportPNGs.java on it to produce PNG evidence of the
solved flow field.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BAT = r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat"
SIM = Path(r"D:\StarCCM Codebuddy\Cases\cyl_vortex_v161R_v26_solved.sim")
MACRO = Path(r"D:\StarCCM Codebuddy\macros\PatchV161R_ExportPNGs.java")
OUT_DIR = Path(r"D:\StarCCM Codebuddy\Cases\Results\secondary_evidence")
LOG_OUT = Path(r"D:\StarCCM Codebuddy\Cases\Results\v161r_export.out")
LOG_ERR = Path(r"D:\StarCCM Codebuddy\Cases\Results\v161r_export.err")
RUN_LOG = Path(r"D:\StarCCM Codebuddy\Cases\Results\v161r_export.log")
CODEBUDDY_ROOT = Path(r"D:\StarCCM Codebuddy")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--timeout", type=int, default=900)
    p.add_argument("--keep-sim", action="store_true")
    args = p.parse_args()

    if not Path(BAT).exists():
        print(f"FATAL: {BAT} missing", file=sys.stderr); return 1
    if not SIM.exists():
        print(f"FATAL: {SIM} missing", file=sys.stderr); return 1

    macro = MACRO
    if not macro.exists():
        alt = Path(r"D:\StarCCM Codebuddy\macros\PatchV159R_Export3PNG.java")
        if alt.exists():
            print(f"  fallback to {alt}")
            macro = alt
        else:
            print(f"FATAL: no export macro found", file=sys.stderr); return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"BAT    : {BAT}")
    print(f"SIM    : {SIM}")
    print(f"MACRO  : {MACRO}")
    print(f"OUT_DIR: {OUT_DIR}")
    print(f"timeout: {args.timeout}s")
    sys.stdout.flush()

    env = os.environ.copy()
    env["JAVA_TOOL_OPTIONS"] = "-Dfile.encoding=UTF-8"
    env["JAVAC_OPTIONS"] = "-encoding UTF-8"

    cmd = [BAT, str(SIM), "-batch", str(macro)]
    t0 = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(CODEBUDDY_ROOT), env=env,
                              capture_output=True, timeout=args.timeout, check=False)
    except subprocess.TimeoutExpired:
        print(f"TIMEOUT after {args.timeout}s"); return 2
    elapsed = time.monotonic() - t0

    def safe_decode(b: bytes) -> str:
        for enc in ("utf-8", "gbk", "cp1252", "latin-1"):
            try: return b.decode(enc, errors="replace")
            except UnicodeDecodeError: continue
        return b.decode("utf-8", errors="replace")

    LOG_OUT.write_text(safe_decode(proc.stdout), encoding="utf-8")
    LOG_ERR.write_text(safe_decode(proc.stderr), encoding="utf-8")
    print(f"elapsed: {elapsed:.1f}s, RC: {proc.returncode}")
    if RUN_LOG.exists():
        run_log = RUN_LOG.read_text(encoding="utf-8", errors="replace")
        print("--- v161r_export.log (last 30 lines) ---")
        for line in run_log.splitlines()[-30:]:
            print(f"  {line}")

    # List PNGs in OUT_DIR
    pngs = sorted(OUT_DIR.glob("*.png"))
    print(f"\n=== Secondary evidence PNGs in {OUT_DIR} ===")
    for p in pngs:
        print(f"  {p.name}  ({p.stat().st_size} bytes)")

    return 0 if proc.returncode == 0 else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
