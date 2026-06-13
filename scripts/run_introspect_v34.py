"""run_introspect_v34.py - load naca2412_v34_with_reports.sim and run
IntrospectV34Mesh.java. STAR-CCM+ 2402 R8 only — uses starccm+.bat.
"""
import os
import subprocess
import sys
import time
from pathlib import Path


def main():
    starccm_bat = Path(r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat")
    sim_path = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v34_with_reports.sim")
    macro = Path(r"D:\StarCCM Codebuddy\macros\IntrospectV34Mesh.java")
    log = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34.log")
    out = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34.out")
    err = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34.err")

    if not starccm_bat.exists():
        print(f"FATAL: {starccm_bat} not found"); sys.exit(1)
    if not sim_path.exists():
        print(f"FATAL: {sim_path} not found"); sys.exit(1)
    if not macro.exists():
        print(f"FATAL: {macro} not found"); sys.exit(1)

    # Delete prior sim/_smoke if any
    sim_working = sim_path.with_name(sim_path.stem + "_introspect.sim")
    if sim_working.exists():
        sim_working.unlink()

    cmd = [str(starccm_bat), "-new", str(sim_working), "-batch", str(macro)]
    # Better: load the v34 sim AS-IS (no -new) - just open + run macro
    cmd = [str(starccm_bat), str(sim_path), "-batch", str(macro)]

    print(f"INTROSPECT_V34")
    print(f"SIM  = {sim_path}")
    print(f"MACRO= {macro}")
    print(f"CMD  = {' '.join(cmd)}")
    print(f"LOG  = {log}")
    print(f"OUT  = {out}")
    print(f"ERR  = {err}")
    t0 = time.time()
    try:
        with open(out, "wb") as fo, open(err, "wb") as fe:
            proc = subprocess.run(cmd, stdout=fo, stderr=fe, timeout=600)
        rc = proc.returncode
    except subprocess.TimeoutExpired:
        rc = -1
    elapsed = time.time() - t0
    print(f"elapsed: {elapsed:.1f}s, RC: {rc}")
    if log.exists():
        try:
            txt = log.read_text(encoding="utf-8", errors="replace")
            print(f"--- introspect log ({len(txt)} chars) ---")
            for line in txt.splitlines()[-100:]:
                print(line)
        except Exception as e:
            print(f"log read FAIL: {e}")
    else:
        print(f"WARN: {log} not produced")
    sys.exit(rc)


if __name__ == "__main__":
    main()
