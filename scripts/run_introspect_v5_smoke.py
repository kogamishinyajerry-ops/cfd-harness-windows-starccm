"""run_introspect_v5_smoke.py - 1-line introspect to confirm batch+write works.
"""
import subprocess, sys, time
from pathlib import Path

starccm_bat = Path(r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat")
sim_path = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v34_with_reports.sim")
macro = Path(r"D:\StarCCM Codebuddy\macros\IntrospectV5Smoke.java")
log = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_smoke.log")
out = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_smoke.out")
err = Path(r"D:\StarCCM Codebuddy\Cases\Results\introspect_v5_smoke.err")

if log.exists(): log.unlink()
cmd = [str(starccm_bat), str(sim_path), "-batch", str(macro)]
print("CMD:", " ".join(cmd))
t0 = time.time()
try:
    with open(out, "wb") as fo, open(err, "wb") as fe:
        proc = subprocess.run(cmd, stdout=fo, stderr=fe, timeout=240)
    rc = proc.returncode
except subprocess.TimeoutExpired:
    rc = -1
print(f"elapsed: {time.time()-t0:.1f}s, RC: {rc}")
print(f"LOG EXISTS: {log.exists()}")
if log.exists():
    print(f"--- log ({log.stat().st_size} bytes) ---")
    print(log.read_text(encoding='utf-8', errors='replace'))