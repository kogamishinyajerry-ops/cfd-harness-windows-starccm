"""Tests for the auto-verifier top-level entry point."""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_harness.auto_verifier import AutoVerifier
from cfd_harness.auto_verifier.config import VerifierConfig
from cfd_harness.executor.base import ExecutorStatus
from cfd_harness.executor.mock import MockExecutor
from cfd_harness.models import ExecutionResult


def test_mock_run_lid_driven_cavity_at_pass_threshold(ldc_task_spec, gold_root, thresholds_path):
    """A MOCK LDC run with measurements that match the gold → level=PASS,
    but is_validated=False (MOCK ceiling per spec §6.1)."""
    config = VerifierConfig.from_thresholds_yaml(thresholds_path)
    verifier = AutoVerifier(config)
    mock = MockExecutor()
    run = mock.execute(ldc_task_spec)
    # Override the mock's key_quantities with a near-perfect LDC match.
    from dataclasses import replace
    measured = [0.0, -0.042, -0.077, -0.109, -0.141, -0.166, -0.186, -0.206,
                -0.206, -0.169, -0.127, -0.053, 0.034, 0.155, 0.337, 0.617, 1.0]
    # Inject a measured u_centerline into the run report
    run.execution_result.key_quantities["u_centerline"] = measured
    v = verifier.verify(run, ldc_task_spec, gold_anchor=gold_root / "lid_driven_cavity.yaml")
    # u_centerline is within tolerance; v_centerline + primary_vortex
    # are missing → FAIL on those. So level=WARN at best.
    assert v.level in ("WARN", "FAIL"), f"got {v.level}"
    assert v.is_mock is True
    # §6.1 ceiling: MOCK can never validate
    assert v.is_validated is False


def test_real_run_cannot_use_mock_ceiling(ldc_task_spec, gold_root, thresholds_path):
    """A real-solver RunReport (is_mock=False) at level=PASS MUST
    validate (no MOCK ceiling)."""
    from cfd_harness.executor.base import RunReport
    config = VerifierConfig.from_thresholds_yaml(thresholds_path)
    verifier = AutoVerifier(config)
    measured = [0.0, -0.042, -0.077, -0.109, -0.141, -0.166, -0.186, -0.206,
                -0.206, -0.169, -0.127, -0.053, 0.034, 0.155, 0.337, 0.617, 1.0]
    real_result = ExecutionResult(
        success=True,
        is_mock=False,
        residuals={"p": 1e-7, "U": 1e-7},
        key_quantities={"u_centerline": measured, "v_centerline": [0.0] * 17},
    )
    # Simulate a real-solver report by building a RunReport directly.
    # We bypass the executor here — only the auto_verifier logic is under test.
    from cfd_harness.executor.mock import MockExecutor
    mock_report = MockExecutor().execute(ldc_task_spec)
    # Force the run report to be a real-solver one.
    real_report = RunReport(
        mode=mock_report.mode,
        status=mock_report.status,
        contract_hash=mock_report.contract_hash,
        version=mock_report.version,
        execution_result=real_result,
        notes=mock_report.notes,
    )
    v = verifier.verify(real_report, ldc_task_spec, gold_anchor=gold_root / "lid_driven_cavity.yaml")
    # u_centerline passes; v_centerline is zeros (gold is non-zero) → FAIL on v.
    # The verdict should be WARN or FAIL — but is_validated MUST be False
    # because v_centerline fails. The point: is_mock is False here, so
    # the MOCK ceiling doesn't apply.
    assert v.is_mock is False
    assert v.is_validated is False  # v_centerline fails, so not validated


def test_executor_refusal_is_fail(ldc_task_spec, gold_root, thresholds_path):
    """A RunReport with status != OK MUST yield verdict.level=FAIL."""
    from cfd_harness.executor.base import ExecutorMode, RunReport
    config = VerifierConfig.from_thresholds_yaml(thresholds_path)
    verifier = AutoVerifier(config)
    refused = RunReport(
        mode=ExecutorMode.WIN_STARCCM,
        status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
        contract_hash="x",
        version="0.3",
        execution_result=None,
        notes=("stage1plus2_stub",),
    )
    v = verifier.verify(refused, ldc_task_spec, gold_anchor=gold_root / "lid_driven_cavity.yaml")
    assert v.level == "FAIL"
    assert any("executor" in s.category for s in v.suggestions)


def test_mock_ceiling_clamps_pass_to_warn(ldc_task_spec):
    """A MOCK verdict that would otherwise be PASS MUST be clamped to WARN
    at the ``.level`` field itself (not merely flagged), so a mock can never
    publish PASS into the signed audit manifest / metrics / report. The
    identical REAL verdict is left untouched.

    Regression guard for the §6.1 ceiling: before this, verdict.level was
    computed with no mock downgrade and only ``is_validated`` honored the
    'never PASS' contract — verdict_level=PASS could enter the signed
    manifest for a clean mock.
    """
    from cfd_harness.auto_verifier.verifier import Verdict
    from cfd_harness.auto_verifier.gold_standard_comparator import ComparisonResult
    from cfd_harness.auto_verifier.convergence_checker import ConvergenceChecker
    from cfd_harness.auto_verifier.physics_checker import PhysicsChecker

    all_pass_cmp = ComparisonResult(all_pass=True, failing_quantities=[])
    conv = ConvergenceChecker(1e-3).check({"p": 1e-9})  # all_pass=True
    phys = PhysicsChecker().check(ldc_task_spec)

    mock_v = Verdict(level="PASS", comparison=all_pass_cmp, convergence=conv,
                     physics=phys, suggestions=[], is_mock=True)
    assert mock_v.level == "WARN", "a MOCK PASS must clamp to WARN"
    assert mock_v.mock_ceiling_applied is True
    assert mock_v.is_validated is False

    real_v = Verdict(level="PASS", comparison=all_pass_cmp, convergence=conv,
                     physics=phys, suggestions=[], is_mock=False)
    assert real_v.level == "PASS", "a REAL PASS must NOT be clamped"
    assert real_v.mock_ceiling_applied is False
    assert real_v.is_validated is True


def test_no_gold_anchor_yields_fail(ldc_task_spec, thresholds_path):
    """A run with no gold_anchor MUST yield verdict.level=FAIL (or WARN
    with no-anchor warning)."""
    from dataclasses import replace
    config = VerifierConfig.from_thresholds_yaml(thresholds_path)
    verifier = AutoVerifier(config)
    spec_no_gold = replace(ldc_task_spec, gold_anchor="")
    mock = MockExecutor()
    run = mock.execute(spec_no_gold)
    v = verifier.verify(run, spec_no_gold, gold_anchor=None)
    assert v.level in ("FAIL", "WARN")
    assert "__no_gold_anchor__" in v.comparison.failing_quantities or not v.comparison.all_pass
