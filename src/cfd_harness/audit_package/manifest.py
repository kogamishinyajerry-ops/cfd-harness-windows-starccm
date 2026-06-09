"""Manifest: the audit package's manifest dataclass and builder.

Solver-agnostic. Captures everything the audit trail needs:
  - the case_id + executor_mode + contract_hash (the §6.3 identity)
  - the V&V verdict (level, is_validated)
  - the gold comparison (failing quantities)
  - the residual convergence
  - the physics pre-flight

The manifest is the "spec" of a V&V run; serialize.py turns it into
a stable byte representation; sign.py HMAC-signs that byte form.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cfd_harness.executor.base import RunReport
from cfd_harness.auto_verifier.verifier import Verdict
from cfd_harness.models import TaskSpec

__all__ = ["Manifest", "ManifestBuilder"]


# Bump this when the manifest shape changes. The signature is bound
# to a specific SCHEMA_VERSION; bumping it invalidates all
# previously-signed manifests (intended — the contract has moved).
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class Manifest:
    """The audit package's manifest.

    `frozen=True` ensures byte-determinism. The signer hashes
    `serialize_manifest(self)` and signs the bytes; any later
    modification of any field breaks the signature.
    """
    schema_version: int
    case_id: str
    executor_mode: str
    contract_hash: str
    spec_version: str
    verdict_level: str
    is_validated: bool
    is_mock: bool
    comparison_all_pass: bool
    comparison_failing: List[str] = field(default_factory=list)
    convergence_all_pass: bool = False
    convergence_failing: List[str] = field(default_factory=list)
    physics_all_pass: bool = False
    suggestions: List[Dict[str, str]] = field(default_factory=list)
    gold_anchor: Optional[str] = None
    solver_profile: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ManifestBuilder:
    """Build a Manifest from a RunReport + Verdict + TaskSpec."""
    def build(
        self,
        task_spec: TaskSpec,
        run_report: RunReport,
        verdict: Verdict,
    ) -> Manifest:
        return Manifest(
            schema_version=SCHEMA_VERSION,
            case_id=task_spec.case_id,
            executor_mode=run_report.mode.value,
            contract_hash=run_report.contract_hash,
            spec_version=run_report.version,
            verdict_level=verdict.level,
            is_validated=verdict.is_validated,
            is_mock=verdict.is_mock,
            comparison_all_pass=verdict.comparison.all_pass,
            comparison_failing=list(verdict.comparison.failing_quantities),
            convergence_all_pass=verdict.convergence.all_pass,
            convergence_failing=list(verdict.convergence.failing_fields),
            physics_all_pass=verdict.physics.all_pass,
            suggestions=[
                {"category": s.category, "message": s.message, "severity": s.severity}
                for s in verdict.suggestions
            ],
            gold_anchor=task_spec.gold_anchor or None,
            solver_profile=task_spec.solver_profile or None,
        )
