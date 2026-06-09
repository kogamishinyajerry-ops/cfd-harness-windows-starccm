"""Auto-verifier: V&V engine that compares a solver run against a gold standard.

Plane: VERIFICATION. MAY import from EXECUTION (`cfd_harness.executor`)
only.

Public surface (re-exported):
  - AutoVerifier: main entry; runs the full V&V loop on a RunReport
  - GoldStandardComparator: compares residuals + key_quantities vs gold
  - ConvergenceChecker: checks residuals convergence
  - PhysicsChecker: pre-flight physics sanity (BC, mesh, Re range)
  - CorrectionSuggester: when V&V FAILs, suggest corrections
  - VerifierConfig: configuration dataclass
"""
from cfd_harness.auto_verifier.config import VerifierConfig
from cfd_harness.auto_verifier.convergence_checker import ConvergenceChecker
from cfd_harness.auto_verifier.correction_suggester import CorrectionSuggester
from cfd_harness.auto_verifier.gold_standard_comparator import (
    GoldStandardComparator,
    ComparisonResult,
)
from cfd_harness.auto_verifier.physics_checker import PhysicsChecker
from cfd_harness.auto_verifier.verifier import AutoVerifier, Verdict
from cfd_harness.auto_verifier import schemas

__all__ = [
    "VerifierConfig",
    "ConvergenceChecker",
    "CorrectionSuggester",
    "GoldStandardComparator",
    "ComparisonResult",
    "PhysicsChecker",
    "AutoVerifier",
    "Verdict",
    "schemas",
]
