#!/usr/bin/env python
"""Run Rotor37Slice2D.java through STAR-CCM+ 19.02.009 batch.

Driver for the **2D 截面** 雏形 of the NASA Rotor37 transonic axial
compressor surrogate pipeline. 7 月立项期 P3 stub — see
`reports/research/commercial-fan-prop/verdict-2026-07.md` §4.2 P3 +
`planning/track-d-deliverable.md` §3 #9.

8 月数据期 ① (LHS 100-200 样本, PLAID-based) 会复用本 driver, 接
D-1 (PLAID dataset) + D-2 (NASA-TP-1338 gold numbers) 后跑真机.

Two executor modes:
  - ``--executor mock``        (default) — never spawns STAR-CCM+.
    Constructs a TaskSpec, hands it to ``MockExecutor`` (always
    available), prints the RunReport. Smoke-test only; verdict
    ceiling = WARN per EXECUTOR_ABSTRACTION §6.1.
  - ``--executor win_starccm`` — actually spawns STAR-CCM+ via
    ``CodebuddyRepl.run_macro(...)`` with ``force_new=True`` and the
    8 月-tuning env override ``ROTOR37_ITERS``.  **opt-in**; not
    invoked by the smoke test (would take 5-30 min + license cost).

The driver is solver-agnostic on the mock side (EXECUTION plane,
``cfd_harness.executor``) and STAR-CCM+ specific on the real side
(ADAPTER_STARCCM plane, ``packages.starccm_bridge.repl``) — per
``docs/adr/ADR-001-four-plane-import-enforcement.md``.

Usage
-----
  # Smoke test (default mock, no spawn)
  python scripts/run_rotor37_macro.py \\
      --case-id rotor37_slice --executor mock --iters 0

  # Real run (opt-in; takes 5-30 min on STAR-CCM+ 2402 R8)
  python scripts/run_rotor37_macro.py \\
      --case-id rotor37_slice --executor win_starccm --iters 200
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# --- paths (mirror run_naca_macro.py layout) --------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
MACRO = REPO_ROOT / "macros" / "Rotor37Slice2D.java"
GOLD_STANDARDS_DIR = REPO_ROOT / "knowledge" / "gold_standards"
ROTOR37_YAML = GOLD_STANDARDS_DIR / "rotor37.yaml"
SIM = REPO_ROOT / "Cases" / "Results" / "rotor37_slice_smoke.sim"

# 8 月会接 D-1 PLAID dataset. P1 stub (2026-06-12) 已把 NASA-TP-1338
# + Suder 1995 数字转录到 rotor37.yaml — 见 P1 deliverable. 本 driver 在
# MOCK 路径下读 yaml 拿 design point (informational only).
DEFAULT_DESIGN_POINT = {
    "n_blades": 36,
    "rpm": 17188.7,
    "tip_speed_m_s": 454.0,
    "mass_flow_kg_s": 20.19,        # NUMECA baseline (P1 yaml 3 sources)
    "PR_design": 2.106,             # NASA-TP-1338 design point (P1 yaml)
    "eta_is_design": 0.877,         # NUMECA 验证 (P1 yaml)
}


def _print_design_point(dp: dict) -> None:
    print("=== Rotor37 design point (8 月接 PLAID + NASA-TP-1338) ===")
    for k, v in dp.items():
        print(f"  {k:18s} = {v}")
    print("==========================================================")


def _run_mock(case_id: str, iters: int) -> int:
    """Default path. Never spawns STAR-CCM+. Uses MockExecutor."""
    print(f"[MOCK] case_id={case_id} iters={iters}")
    print(f"[MOCK] macro   = {MACRO}")
    print(f"[MOCK] sim     = {SIM}  (NOT created on MOCK)")
    print(f"[MOCK] gold    = {ROTOR37_YAML}  "
          f"({'present' if ROTOR37_YAML.exists() else 'absent'})")
    _print_design_point(DEFAULT_DESIGN_POINT)

    # If P1 stub has produced rotor37.yaml, peek at the design point
    # quantities for self-check. We do NOT mutate the file; we only
    # read it informational.  yaml.safe_load_all handles the multi-
    # document format used by gold_standards (one file = N quantities).
    if ROTOR37_YAML.exists():
        try:
            import yaml  # PyYAML, optional dep
            with ROTOR37_YAML.open("r", encoding="utf-8") as fh:
                docs = list(yaml.safe_load_all(fh))
            quantities = [d.get("quantity") for d in docs if isinstance(d, dict)]
            print(f"[MOCK] yaml quantities ({len(quantities)}): "
                  f"{', '.join(str(q) for q in quantities if q) or '(none parsed)'}")
        except Exception as e:
            print(f"[MOCK] yaml peek skipped: {e}")

    # Lazy import: cfd_harness is in src/ layout, requires the venv
    # to be activated (or PYTHONPATH=src).  We do best-effort import
    # so a venv-less invocation can still print the path and exit 0.
    try:
        from cfd_harness.executor import MockExecutor          # noqa: WPS433
        from cfd_harness.executor.base import ExecutorStatus    # noqa: WPS433
        from cfd_harness.models import (                        # noqa: WPS433
            FlowType, GeometryType, TaskSpec,
        )
    except Exception as e:  # pragma: no cover (smoke-only)
        print(f"[MOCK] SKIP cfd_harness import ({e}); "
              "verdict ceiling = WARN by default (no real execution).")
        return 0

    # The actual mock run: build TaskSpec + call executor.
    spec = TaskSpec(
        case_id=case_id,
        flow_type=FlowType.INTERNAL,            # Rotor37 = compressor internal
        geometry_type=GeometryType.IMPORTED_GEOMETRY,  # 8 月接 PLAID/STL
        parameters={"iters": iters, **DEFAULT_DESIGN_POINT},
        gold_anchor=str(ROTOR37_YAML),
        solver_profile="",
        mesh_density="mesh_160",                 # 8 月 1M-cell per Suder 1995
        timeout_s=60,
    )
    t0 = time.monotonic()
    report = MockExecutor().execute(spec)
    elapsed = time.monotonic() - t0
    print(f"[MOCK] status      = {report.status.name}")
    print(f"[MOCK] mode        = {report.mode.name}")
    print(f"[MOCK] elapsed     = {elapsed*1000:.1f}ms")
    print(f"[MOCK] is_mock     = {report.execution_result.is_mock}")
    print(f"[MOCK] key_q       = {report.execution_result.key_quantities}")
    print(f"[MOCK] residuals   = {report.execution_result.residuals}")
    print(f"[MOCK] notes       = {list(report.notes)}")
    # 关键提示: 8 月接真机前必须 (a) D-2 填数字 (b) gain user ratification.
    print("[MOCK] REMINDER: 7 月期 L0 边界内,本 driver 仅 stub. "
          "8 月数据期 ① 接 D-1 PLAID + D-2 NASA-TP-1338 gold.")
    return 0 if report.status == ExecutorStatus.OK else 1


def _run_win_starccm(case_id: str, iters: int, timeout_s: int) -> int:
    """Opt-in real run. Spawns STAR-CCM+ via Codebuddy REPL bridge."""
    if not MACRO.exists():
        print(f"FATAL: macro not found: {MACRO}", file=sys.stderr)
        return 1
    if not SIM.parent.exists():
        SIM.parent.mkdir(parents=True, exist_ok=True)

    print(f"[WIN_STARCCM] case_id={case_id} iters={iters} timeout={timeout_s}s")
    print(f"[WIN_STARCCM] macro = {MACRO}")
    print(f"[WIN_STARCCM] sim   = {SIM}  (force_new=True)")
    _print_design_point(DEFAULT_DESIGN_POINT)

    # Lazy import: bridge requires the editable install (pip install -e).
    try:
        from starccm_bridge.repl import CodebuddyRepl  # noqa: WPS433
    except Exception as e:                              # pragma: no cover
        print(f"FATAL: cannot import starccm_bridge: {e}", file=sys.stderr)
        print("       Hint: pip install -e packages/starccm-bridge", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["ROTOR37_ITERS"] = str(iters)
    env["JAVA_TOOL_OPTIONS"] = "-Dfile.encoding=UTF-8"
    env["JAVAC_OPTIONS"] = "-encoding UTF-8"

    repl = CodebuddyRepl()
    t0 = time.monotonic()
    try:
        resp = repl.run_macro(
            sim_path=str(SIM),
            macro_path=str(MACRO),
            macro_args="",
            timeout_s=timeout_s,
            env=env,
            force_new=True,
        )
    except Exception as e:                              # pragma: no cover
        print(f"FATAL: run_macro raised: {e}", file=sys.stderr)
        return 3
    elapsed = time.monotonic() - t0

    print(f"[WIN_STARCCM] elapsed    = {elapsed:.1f}s")
    print(f"[WIN_STARCCM] returncode = {resp.returncode}")
    print(f"[WIN_STARCCM] ok         = {resp.ok}")
    print(f"[WIN_STARCCM] data       = {resp.data}")
    if not resp.ok:
        print(f"[WIN_STARCCM] error      = {resp.error}", file=sys.stderr)
        print(f"[WIN_STARCCM] stderr_head=\n{resp.raw_stderr[:1500]}",
              file=sys.stderr)
        return 4
    return 0


def main() -> int:
    p = argparse.ArgumentParser(
        description="Rotor37 2D-slice driver (cfd-harness-windows-starccm P3 stub)",
    )
    p.add_argument("--case-id", default="rotor37_slice",
                   help="Case id routed to the executor (default: rotor37_slice)")
    p.add_argument("--executor", choices=["mock", "win_starccm"], default="mock",
                   help="Executor mode (default: mock — no spawn)")
    p.add_argument("--iters", type=int, default=200,
                   help="Iteration count for the macro's solver (default: 200)")
    p.add_argument("--yaml", default=str(ROTOR37_YAML),
                   help="Path to gold-standard yaml (informational only on MOCK)")
    p.add_argument("--timeout", type=int, default=1800,
                   help="WIN_STARCCM spawn timeout in seconds (default: 1800)")
    args = p.parse_args()

    print(f"case_id  = {args.case_id}")
    print(f"executor = {args.executor}")
    print(f"iters    = {args.iters}")
    print(f"yaml     = {args.yaml}")
    print("---")

    if args.executor == "mock":
        return _run_mock(args.case_id, args.iters)
    return _run_win_starccm(args.case_id, args.iters, args.timeout)


if __name__ == "__main__":
    raise SystemExit(main())
