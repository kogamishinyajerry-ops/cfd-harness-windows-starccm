"""run_introspect_v5.py - load v34 NACA solved sim, run IntrospectV5CFLv2.java.
STAR-CCM+ 2402 R8. Slim introspect (240s timeout).
"""
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    starccm_bat = Path(r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat")
    sim_path = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v34_with_reports.sim")
    macro = Path(r"D:\StarCCM Codebuddy\macros\IntrospectV5CFLv2.java")
    log = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_cfl.log")
    out = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_cfl.out")
    err = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_cfl.err")

    for p, label in [(starccm_bat, "starccm+"), (sim_path, "sim"), (macro, "macro")]:
        if not p.exists():
            print(f"FATAL: {label} not found: {p}"); sys.exit(1)

    cmd = [str(starccm_bat), str(sim_path), "-batch", str(macro)]
    print(f"INTROSPECT_V5 v2")
    print(f"SIM  = {sim_path}")
    print(f"MACRO= {macro}")
    print(f"CMD  = {' '.join(cmd)}")
    t0 = time.time()
    try:
        with open(out, "wb") as fo, open(err, "wb") as fe:
            proc = subprocess.run(cmd, stdout=fo, stderr=fe, timeout=240)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        rc = -1
    elapsed = time.time() - t0
    print(f"elapsed: {elapsed:.1f}s, RC: {rc}")
    if log.exists():
        print(f"--- introspect log ({log.stat().st_size} bytes) ---")
        print(log.read_text(encoding='utf-8', errors='replace'))
    else:
        print("LOG FILE NOT PRODUCED (likely macro didn't run or hung)")


if __name__ == "__main__":
    main()