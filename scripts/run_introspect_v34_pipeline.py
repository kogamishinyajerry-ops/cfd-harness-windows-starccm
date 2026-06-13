"""run_introspect_v34_pipeline.py - load naca2412_v34_500iter.sim (v34 working
mesh) and run IntrospectV34MeshPipeline.java.
"""
import subprocess
import sys
import time
from pathlib import Path


def main():
    starccm_bat = Path(r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat")
    sim_path = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v34_500iter.sim")
    macro = Path(r"D:\StarCCM Codebuddy\macros\IntrospectV34MeshPipeline.java")
    log = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34_pipeline.log")
    out = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34_pipeline.out")
    err = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v34_pipeline.err")

    cmd = [str(starccm_bat), str(sim_path), "-batch", str(macro)]
    print(f"INTROSPECT_V34_PIPELINE")
    print(f"SIM  = {sim_path}")
    print(f"CMD  = {' '.join(cmd)}")
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
