"""CLI entry point for cfd-harness-windows-starccm.

Usage:
  python -m cfd_harness.cli.run --case lid_driven_cavity --executor mock
  python -m cfd_harness.cli.run --case naca0012_airfoil --executor mock
  python -m cfd_harness.cli.run --case lid_driven_cavity --executor win_starccm
    (Stage 3+ only)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

from cfd_harness.auto_verifier import AutoVerifier
from cfd_harness.auto_verifier.config import VerifierConfig
from cfd_harness.audit_package import ManifestBuilder, Signer
from cfd_harness.audit_package.sign import MIN_KEY_BYTES, DEV_UNSIGNED_KEY
from cfd_harness.executor import (
    DockerOpenFOAMExecutor,
    FutureRemoteExecutor,
    HybridInitExecutor,
    MockExecutor,
    WinStarCCMExecutor,
)
from cfd_harness.executor.base import ExecutorMode, spec_is_available
from cfd_harness.metrics import MetricsAccumulator
from cfd_harness.models import FlowType, GeometryType, TaskSpec
from cfd_harness.report_engine import DataCollector, ReportGenerator

__all__ = ["main", "build_parser", "ANCHOR_CASES"]


# Anchor cases (the 3 the chief engineer will run E2E in Stage 4) +
# 13 new cases ported 2026-06-11 from cfd-harness-unified (mock-first
# stage 2.x — see DEC-006 if you want the formal rationale).
ANCHOR_CASES = {
    # 3 anchors (Stage 4 E2E priority)
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
    # 13 new cases (mock-first; gold_standards/ + _CASE_PRESETS both shipped)
    # ---- INTERNAL group (5 new) ----
    "backward_facing_step": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 600, "expansion_ratio": 2.0},
    },
    "backward_facing_step_steady": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": [100, 200, 600], "expansion_ratio": 2.0},
    },
    "duct_flow": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": [1500, 10000], "diameter": 0.01},
    },
    "fully_developed_plane_channel_flow": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 100, "half_height": 1.0},
    },
    "plane_channel_flow": {
        "flow_type": FlowType.INTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re_tau": 590},
    },
    # ---- EXTERNAL group (4 new) ----
    "axisymmetric_impinging_jet": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 10000, "H_over_D": 2.0, "T_wall": 350.0, "T_jet": 300.0},
    },
    "cylinder_crossflow": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 3900, "diameter": 1.0, "freestream_u": 1.0},
    },
    "impinging_jet": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": 8000, "H_over_W": 4.0, "T_wall": 350.0, "T_jet": 300.0},
    },
    "turbulent_flat_plate": {
        "flow_type": FlowType.EXTERNAL,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re_x": 1.0e7},
    },
    # ---- NATURAL_CONVECTION group (2 new) ----
    "differential_heated_cavity": {
        "flow_type": FlowType.NATURAL_CONVECTION,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Ra": [1.0e3, 1.0e5], "T_hot": 1.0, "T_cold": 0.0},
    },
    "rayleigh_benard_convection": {
        "flow_type": FlowType.NATURAL_CONVECTION,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Ra_range": [1.0e5, 1.0e9], "T_hot": 1.0, "T_cold": 0.0},
    },
    # ---- CONJUGATE group (2 new) ----
    "cht_pipe_gnielinski": {
        "flow_type": FlowType.CONJUGATE,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"Re": [10000, 100000], "Pr": 0.7, "T_wall": 350.0, "T_inlet": 300.0},
    },
    "cht_straight_fin": {
        "flow_type": FlowType.CONJUGATE,
        "geometry_type": GeometryType.SIMPLE_GRID,
        "parameters": {"k_fin": 200.0, "h_conv": 100.0, "L_c": 0.05, "thickness": 0.003, "T_wall": 400.0, "T_inf": 300.0},
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
        default=None,
        help=(
            "HMAC key for the audit manifest signer. Prefer the "
            f"{_SIGN_KEY_ENV} env var. If neither is set, an UNTRUSTED "
            "dev-unsigned key is used (audit marked trusted=false)."
        ),
    )
    return p


# Env var that supplies the production HMAC signing key (preferred over a
# CLI flag, which leaks into shell history / process listings).
_SIGN_KEY_ENV = "CFD_HARNESS_SIGN_KEY"

# The dev-unsigned fallback key lives in audit_package.sign (DEV_UNSIGNED_KEY)
# so verifiers can recognise it without importing this CLI. See DEC-010.

# case_id flows into the audit_dir path; constrain it so a programmatic
# caller (TaskSpec has no field validation) cannot traverse out of the tree.
_SAFE_CASE_ID = re.compile(r"^[A-Za-z0-9_.\-]{1,64}$")


def _resolve_sign_key(cli_key: Optional[str]) -> tuple[bytes, str]:
    """Resolve the HMAC signing key and its provenance.

    Priority: --sign-key > $CFD_HARNESS_SIGN_KEY > the dev-unsigned key.
    Returns (key_bytes, key_source) where key_source is "provided" or
    "dev-unsigned".
    """
    key_str = cli_key or os.environ.get(_SIGN_KEY_ENV)
    if key_str:
        return key_str.encode("utf-8"), "provided"
    return DEV_UNSIGNED_KEY, "dev-unsigned"


def _safe_case_id(case_id: str) -> str:
    if not _SAFE_CASE_ID.match(case_id):
        raise ValueError(f"case_id contains unsafe characters for a path: {case_id!r}")
    return case_id


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

    # Audit (signed manifest). The HMAC is only trustworthy if the key is
    # secret; resolve it from --sign-key / env, else fall back to the
    # explicitly UNTRUSTED dev key (see DEC-010).
    manifest = ManifestBuilder().build(task_spec, run_report, verdict)
    if not spec_is_available():
        print(
            "[audit][WARN] contract spec (docs/specs/EXECUTOR_ABSTRACTION.md) not "
            "readable; contract_hash is spec-unbound — treat this audit as spec-less.",
            file=sys.stderr,
        )
    key_bytes, key_source = _resolve_sign_key(args.sign_key)
    if len(key_bytes) < MIN_KEY_BYTES:
        print(
            f"[error] signing key must be >= {MIN_KEY_BYTES} bytes; got "
            f"{len(key_bytes)}. Provide a longer --sign-key or {_SIGN_KEY_ENV}.",
            file=sys.stderr,
        )
        return 2
    if key_source == "dev-unsigned":
        print(
            "[audit][WARN] no signing key (--sign-key / $CFD_HARNESS_SIGN_KEY); "
            "using the DEV-UNSIGNED key — this audit is NOT cryptographically "
            "trusted (key_source=dev-unsigned, trusted=false).",
            file=sys.stderr,
        )
    signer = Signer(key_bytes)
    signature = signer.sign(manifest)
    trusted = key_source == "provided"
    print(
        f"[audit] manifest.schema_version={manifest.schema_version} "
        f"contract_hash={manifest.contract_hash[:12]}... key_id={signature.key_id} "
        f"trusted={trusted} hmac[:12]={signature.hmac[:12]}"
    )

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
        comparison_quantities=[
            {
                "name": q.name,
                "measured": q.measured,
                "gold": q.gold,
                "relative_error": q.relative_error,
                "tolerance": q.tolerance,
                "all_pass": q.all_pass,
            }
            for q in verdict.comparison.quantities
        ],
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

    # Audit file (signed manifest). Lives under reports/audit/<case>/<ts>/
    # so the data.json + audit.json can be cross-checked independently
    # (byte-deterministic signed audit package is one of the 5 ground rules).
    audit_dir = output_root / "audit" / _safe_case_id(task_spec.case_id) / data_path.parent.name
    audit_dir.mkdir(parents=True, exist_ok=True)
    audit_file = audit_dir / "audit.json"
    audit_payload = {
        "manifest": manifest.to_dict(),
        "signature": {
            "digest": signature.digest,
            "hmac": signature.hmac,
            "key_id": signature.key_id,
            "algorithm": signature.algorithm,
            "signed_at": signature.signed_at,
        },
        # Trust metadata. The AUTHORITATIVE check is key_id vs the verifier's
        # expected production key fingerprint; `trusted` is advisory. A
        # production verifier MUST reject any audit whose key_id is the
        # dev-unsigned key_id (or key_source != "provided").
        "signing": {
            "key_source": key_source,        # "provided" | "dev-unsigned"
            "trusted": trusted,
            "min_key_bytes": MIN_KEY_BYTES,
        },
        # A runnable verification recipe. The secret key must be obtained
        # out-of-band (it is never written to the audit).
        "verify_recipe": (
            "import json; from cfd_harness.audit_package import Manifest, Signature; "
            "d = json.load(open('audit.json')); key = b'<your-secret-key>'; "
            "sig = Signature(**d['signature']); m = Manifest(**d['manifest']); "
            "assert sig.verify(m, key), 'TAMPERED-OR-WRONG-KEY'"
        ),
    }
    audit_file.write_text(
        json.dumps(audit_payload, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(f"[audit] {audit_file}")
    print(f"[audit] schema_v{manifest.schema_version} hmac={signature.hmac[:16]}... digest={signature.digest[:16]}...")

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
