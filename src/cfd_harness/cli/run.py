"""CLI entry point for cfd-harness-windows-starccm.

Usage:
  python -m cfd_harness.cli.run --case lid_driven_cavity --executor mock
  python -m cfd_harness.cli.run --case naca0012_airfoil --executor mock
  python -m cfd_harness.cli.run --case lid_driven_cavity --executor win_starccm
    (Stage 3+ only)
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from cfd_harness.auto_verifier import AutoVerifier
from cfd_harness.auto_verifier.config import VerifierConfig
from cfd_harness.audit_package import ManifestBuilder, Signer
from cfd_harness.executor import (
    DockerOpenFOAMExecutor,
    FutureRemoteExecutor,
    HybridInitExecutor,
    MockExecutor,
    WinStarCCMExecutor,
)
from cfd_harness.executor.base import ExecutorMode
from cfd_harness.metrics import MetricsAccumulator
from cfd_harness.models import FlowType, GeometryType, TaskSpec
from cfd_harness.report_engine import DataCollector, ReportGenerator

__all__ = ["main", "build_parser", "ANCHOR_CASES"]


# Anchor cases (the 3 the chief engineer will run E2E in Stage 4).
ANCHOR_CASES = {
    "lid_driven_cavity": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 100, "boundary_conditions": {"top_wall_u": 1.0, "other_walls_u": 0.0}},
    },
    "naca0012_airfoil": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.IMPORTED_GEOMETRY,
        "parameters": {"Re": 6.0e6, "alpha": 2.0, "Mach": 0.15},
    },
    "circular_cylinder_wake": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 200, "diameter": 1.0, "freestream_u": 1.0},
    },
}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cfd-harness",
        description="Run a V&V benchmark through the harness",
    )
    p.add_argument("--case", required=True, help="case_id (e.g. lid_driven_cavity)")
    p.add_argument(
        "--executor",
        default="mock",
        choices=[m.value for m in ExecutorMode],
        help="ExecutorMode (default: mock)",
    )
    p.add_argument(
        "--gold-anchor",
        default=None,
        help="Path to the gold-standard YAML (default: knowledge/gold_standards/<case>.yaml)",
    )
    p.add_argument(
        "--thresholds",
        default=None,
        help="Path to the attestor thresholds YAML (default: knowledge/attestor_thresholds.yaml)",
    )
    p.add_argument(
        "--output",
        default="reports",
        help="Output root for data.json + report (default: reports/)",
    )
    p.add_argument(
        "--sign-key",
        default="cfd-harness-dev-key",
        help="HMAC key for the audit manifest signer (default: dev key; override in prod)",
    )
    return p


def _make_executor(mode: ExecutorMode):
    if mode == ExecutorMode.MOCK:
        return MockExecutor()
    if mode == ExecutorMode.DOCKER_OPENFOAM:
        return DockerOpenFOAMExecutor()
    if mode == ExecutorMode.WIN_STARCCM:
        return WinStarCCMExecutor()
    if mode == ExecutorMode.HYBRID_INIT:
        return HybridInitExecutor()
    if mode == ExecutorMode.FUTURE_REMOTE:
        return FutureRemoteExecutor()
    raise ValueError(f"Unknown ExecutorMode: {mode!r}")


def main(argv: Optional[list] = None) -> int:
    args = build_parser().parse_args(argv)
    case_def = ANCHOR_CASES.get(args.case)
    if case_def is None:
        print(f"[error] unknown case_id: {args.case!r}. Known: {sorted(ANCHOR_CASES)}", file=sys.stderr)
        return 2

    # Resolve paths
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    gold_path = Path(args.gold_anchor) if args.gold_anchor else (
        repo_root / "knowledge" / "gold_standards" / f"{args.case}.yaml"
    )
    thresholds_path = (
        Path(args.thresholds) if args.thresholds
        else repo_root / "knowledge" / "attestor_thresholds.yaml"
    )

    task_spec = TaskSpec(
        case_id=args.case,
        flow_type=case_def["flow_type"],
        geometry_type=case_def["geometry_type"],
        parameters=case_def["parameters"],
        gold_anchor=str(gold_path),
        solver_profile="",
        mesh_density="default",
    )

    # Run
    mode = ExecutorMode(args.executor)
    executor = _make_executor(mode)
    run_report = executor.execute(task_spec)
    print(f"[executor] mode={run_report.mode.value} status={run_report.status.value} notes={list(run_report.notes)}")

    # Verify
    config = VerifierConfig.from_thresholds_yaml(thresholds_path)
    verifier = AutoVerifier(config)
    verdict = verifier.verify(run_report, task_spec, gold_anchor=gold_path)
    print(f"[verdict] level={verdict.level} is_validated={verdict.is_validated} is_mock={verdict.is_mock}")
    for s in verdict.suggestions:
        print(f"  - {s}")

    # Audit
    manifest = ManifestBuilder().build(task_spec, run_report, verdict)
    signer = Signer(args.sign_key.encode("utf-8") if isinstance(args.sign_key, str) else args.sign_key)
    signature = signer.sign(manifest)
    print(f"[audit] manifest.schema_version={manifest.schema_version} contract_hash={manifest.contract_hash[:12]}... sig.hmac[:12]={signature.hmac[:12]}")

    # Report
    output_root = Path(args.output)
    data_collector = DataCollector(output_root)
    from cfd_harness.auto_verifier.schemas import VerifierReport
    verifier_report = VerifierReport(
        case_id=task_spec.case_id,
        executor_mode=run_report.mode.value,
        is_mock=verdict.is_mock,
        level=verdict.level,
        is_validated=verdict.is_validated,
        comparison_all_pass=verdict.comparison.all_pass,
        comparison_failing=list(verdict.comparison.failing_quantities),
        convergence_all_pass=verdict.convergence.all_pass,
        convergence_failing=list(verdict.convergence.failing_fields),
        physics_all_pass=verdict.physics.all_pass,
        physics_failures=list(verdict.physics.failures),
        physics_warnings=list(verdict.physics.warnings),
        suggestions=[{"category": s.category, "message": s.message, "severity": s.severity} for s in verdict.suggestions],
        contract_hash=run_report.contract_hash,
        spec_version=run_report.version,
    )
    data_path = data_collector.collect(task_spec, run_report, verifier_report)
    report_md_path = data_path.with_suffix(".md")
    report_md_path.write_text(ReportGenerator().render(data_path), encoding="utf-8")
    print(f"[report] {data_path}")
    print(f"[report] {report_md_path}")

    # Metrics
    metrics = MetricsAccumulator()
    metrics.record(verdict.level, is_mock=verdict.is_mock)
    snap = metrics.snapshot()
    print(f"[metrics] {snap.to_dict()}")

    # Exit code
    if not verdict.is_validated and not verdict.is_mock:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
