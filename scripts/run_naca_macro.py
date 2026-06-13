#!/usr/bin/env python
"""Run NacaTrueE2E.java through STAR-CCM+ 19.02.009 batch.

Bypasses the starccm-bridge (Python 3.12+ required) and calls the
.bat directly. Mirrors the bridge's run_macro semantics:
  [bat, sim, -new, -batch, macro] with NACA_ITERS env override.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

BAT = r"C:\Program Files\Siemens\19.02.009-R8\STAR-CCM+19.02.009-R8\star\bin\starccm+.bat"
MACRO = Path(r"D:\StarCCM Codebuddy\macros\NacaTrueE2E.java")
SIM = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true_smoke.sim")
LOG_OUT = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca_smoke_v1.out")
LOG_ERR = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca_smoke_v1.err")
RUN_LOG = Path(r"D:\StarCCM Codebuddy\Cases\Results\naca_true_v1.log")
CODEBUDDY_ROOT = Path(r"D:\StarCCM Codebuddy")


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--iters", type=int, default=100, help="NACA_ITERS env override")
    p.add_argument("--timeout", type=int, default=600, help="seconds")
    p.add_argument("--keep-sim", action="store_true", help="don't trash existing .sim")
    args = p.parse_args()

    if not Path(BAT).exists():
        print(f"FATAL: {BAT} not found", file=sys.stderr)
        return 1
    if not MACRO.exists():
        print(f"FATAL: {MACRO} not found", file=sys.stderr)
        return 1

    if not args.keep_sim and SIM.exists():
        SIM.unlink()
        print(f"  removed existing {SIM.name}")

    print(f"BAT : {BAT}")
    print(f"MACRO: {MACRO}")
    print(f"SIM : {SIM}  (force_new=True)")
    print(f"NACA_ITERS = {args.iters}")
    print(f"timeout    = {args.timeout}s")
    print("---")
    sys.stdout.flush()

    env = os.environ.copy()
    env["NACA_ITERS"] = str(args.iters)
    env["JAVA_TOOL_OPTIONS"] = "-Dfile.encoding=UTF-8"
    env["JAVAC_OPTIONS"] = "-encoding UTF-8"

    cmd = [BAT, str(SIM), "-new", "-batch", str(MACRO)]
    t0 = time.monotonic()
    try:
        # STAR-CCM+ stdout can be GBK-encoded (Chinese locale).
        # Capture as bytes; decode below with errors='replace' so we never
        # crash on non-UTF8 bytes.
        proc = subprocess.run(
            cmd,
            cwd=str(CODEBUDDY_ROOT),
            env=env,
            capture_output=True,
            timeout=args.timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        print(f"TIMEOUT after {args.timeout}s")
        return 2
    elapsed = time.monotonic() - t0

    def _safe_decode(b: bytes) -> str:
        for enc in ("utf-8", "gbk", "cp1252", "latin-1"):
            try:
                return b.decode(enc, errors="replace")
            except UnicodeDecodeError:
                continue
        return b.decode("utf-8", errors="replace")

    stdout_str = _safe_decode(proc.stdout)
    stderr_str = _safe_decode(proc.stderr)

    LOG_OUT.parent.mkdir(parents=True, exist_ok=True)
    LOG_OUT.write_text(stdout_str, encoding="utf-8")
    LOG_ERR.write_text(stderr_str, encoding="utf-8")
    print(f"elapsed: {elapsed:.1f}s, RC: {proc.returncode}")
    print(f"stdout ({len(stdout_str)} chars) -> {LOG_OUT}")
    print(f"stderr ({len(stderr_str)} chars) -> {LOG_ERR}")
    if RUN_LOG.exists():
        print(f"macro log -> {RUN_LOG}")
        # tail last 30 lines of run log
        run_log = RUN_LOG.read_text(encoding="utf-8", errors="replace")
        print("--- naca_true_v1.log (last 30 lines) ---")
        for line in run_log.splitlines()[-30:]:
            print(f"  {line}")

    # Show summary.json if it landed
    summary = CODEBUDDY_ROOT / "Cases" / "Results" / "naca2412_summary.json"
    if summary.exists():
        print("--- naca2412_summary.json ---")
        print(summary.read_text(encoding="utf-8"))

    return 0 if proc.returncode == 0 else proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
