"""AutoVerifier: top-level V&V entry point.

Wires together:
  - PhysicsChecker (pre-flight)
  - ConvergenceChecker (residual floor)
  - GoldStandardComparator (literature-anchored key-quantity comparison)
  - CorrectionSuggester (on FAIL)

Plane: VERIFICATION.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cfd_harness.auto_verifier.config import VerifierConfig
from cfd_harness.auto_verifier.convergence_checker import ConvergenceChecker, ConvergenceResult
from cfd_harness.auto_verifier.correction_suggester import CorrectionSuggester, Suggestion
from cfd_harness.auto_verifier.gold_standard_comparator import (
    ComparisonResult,
    GoldStandardComparator,
)
from cfd_harness.auto_verifier.physics_checker import PhysicsCheckResult, PhysicsChecker
from cfd_harness.executor.base import RunReport
from cfd_harness.executor.base import ExecutorStatus
from cfd_harness.executor.base import ExecutorMode
from cfd_harness.models import TaskSpec

__all__ = ["AutoVerifier", "Verdict"]


# Verdict is the AutoVerifier's top-level outcome. It is solver-agnostic;
# the chief engineer's stage-exit-gate logic reads the verdict and the
# `is_mock` flag together.
class Verdict:
    """The auto-verifier's verdict.

    `level` ∈ {"PASS", "WARN", "FAIL"}.
    `mock_ceiling_applied` is True if the verdict was capped at WARN
    because the run was a MOCK. This is the §6.1 ceiling enforcement.
    """
    def __init__(
        self,
        level: str,
        comparison: ComparisonResult,
        convergence: ConvergenceResult,
        physics: PhysicsCheckResult,
        suggestions: List[Suggestion],
        is_mock: bool = False,
    ) -> None:
        if level not in {"PASS", "WARN", "FAIL"}:
            raise ValueError(f"verdict level must be PASS/WARN/FAIL, got {level!r}")
        self.comparison = comparison
        self.convergence = convergence
        self.physics = physics
        self.suggestions = suggestions
        self.is_mock = is_mock
        # Per EXECUTOR_ABSTRACTION §6.1: a MOCK run has no truth source, so
        # it can never publish PASS. Clamp the level ITSELF (not just record
        # a flag) so the WARN ceiling shows up everywhere verdict.level flows
        # — the signed audit manifest, the metrics, and the markdown report.
        self.mock_ceiling_applied = is_mock and level == "PASS"
        if self.mock_ceiling_applied:
            level = "WARN"
        self.level = level

    @property
    def is_validated(self) -> bool:
        """A run is `validation_status: validated` iff:
        - level is PASS, AND
        - not on a MOCK executor (MOCK can never validate, per spec).
        """
        return self.level == "PASS" and not self.is_mock

    def __bool__(self) -> bool:
        # Verdict is truthy iff validation_status = validated.
        return self.is_validated

    def __str__(self) -> str:
        return (
            f"Verdict({self.level}, "
            f"comparison={'PASS' if self.comparison.all_pass else 'FAIL'}, "
            f"convergence={'PASS' if self.convergence.all_pass else 'FAIL'}, "
            f"physics={'PASS' if self.physics.all_pass else 'FAIL'}, "
            f"is_mock={self.is_mock})"
        )


class AutoVerifier:
    """Top-level V&V entry point.

    Usage:
        verifier = AutoVerifier.from_thresholds_yaml(...)
        verdict = verifier.verify(run_report, task_spec, gold_anchor_path)
    """
    def __init__(self, config: VerifierConfig) -> None:
        self.config = config
        self.comparator = GoldStandardComparator(tolerance_floor=config.tolerance_floor)
        self.suggester = CorrectionSuggester()

    @classmethod
    def from_thresholds_yaml(cls, path: Path) -> "AutoVerifier":
        return cls(VerifierConfig.from_thresholds_yaml(path))

    def verify(
        self,
        run_report: RunReport,
        task_spec: TaskSpec,
        gold_anchor: Optional[Path] = None,
    ) -> Verdict:
        # Refusal paths first
        if run_report.status != ExecutorStatus.OK or run_report.execution_result is None:
            return Verdict(
                level="FAIL",
                comparison=ComparisonResult(all_pass=False, failing_quantities=["__executor_refused__"]),
                convergence=ConvergenceChecker(self.config.residual_floor).check({}),
                physics=PhysicsChecker().check(task_spec),
                suggestions=[Suggestion(
                    category="executor",
                    message=f"Executor refused: status={run_report.status.value}, notes={run_report.notes}",
                    severity="error",
                )],
                is_mock=run_report.mode == ExecutorMode.MOCK,
            )

        # Real path
        result = run_report.execution_result
        is_mock = result.is_mock
        per_case = self.config.for_case(task_spec.case_id)
        conv = ConvergenceChecker(per_case.residual_floor).check(result.residuals)
        phys = PhysicsChecker().check(task_spec)
        gold_path = Path(gold_anchor) if gold_anchor else (
            Path(task_spec.gold_anchor) if task_spec.gold_anchor else None
        )
        cmp_ = self.comparator.compare(gold_path, result.key_quantities) if gold_path else ComparisonResult(
            all_pass=False, failing_quantities=["__no_gold_anchor__"]
        )

        # Compute level
        if not phys.all_pass:
            level = "FAIL"
        elif not conv.all_pass:
            level = "FAIL"
        elif not cmp_.all_pass:
            # Comparison FAIL but convergence + physics OK → WARN
            # (a single quantity off but the solver converged cleanly)
            level = "WARN"
        else:
            level = "PASS"

        suggestions = self.suggester.suggest(cmp_, conv, phys)
        return Verdict(
            level=level,
            comparison=cmp_,
            convergence=conv,
            physics=phys,
            suggestions=suggestions,
            is_mock=is_mock,
        )
