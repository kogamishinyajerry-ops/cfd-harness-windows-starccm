"""CorrectionSuggester: when V&V FAILs, suggest corrections.

Heuristic only. Looks at:
  - which quantities failed and by how much
  - whether the convergence checker flagged any residual fields
  - whether the physics checker flagged any pre-flight failures

Output is a list of human-readable hints; the agent crew uses these
to drive the next iteration. NOT a real optimizer; never makes
autonomous changes to a case.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cfd_harness.auto_verifier.gold_standard_comparator import ComparisonResult
from cfd_harness.auto_verifier.convergence_checker import ConvergenceResult
from cfd_harness.auto_verifier.physics_checker import PhysicsCheckResult

__all__ = ["CorrectionSuggester", "Suggestion"]


@dataclass(frozen=True)
class Suggestion:
    """A single human-readable correction hint."""
    category: str        # "mesh" | "turbulence_model" | "bc" | "convergence" | "physics"
    message: str
    severity: str        # "info" | "warn" | "error"

    def __str__(self) -> str:
        return f"[{self.severity}] {self.category}: {self.message}"


class CorrectionSuggester:
    """Generate suggestions from V&V failure modes."""
    def suggest(
        self,
        comparison: ComparisonResult,
        convergence: ConvergenceResult,
        physics: PhysicsCheckResult,
    ) -> List[Suggestion]:
        out: List[Suggestion] = []
        # Convergence
        for f in convergence.failing_fields:
            if f == "__no_residuals__":
                out.append(Suggestion(
                    category="convergence",
                    message="No residuals reported — solver may have diverged or returned early",
                    severity="error",
                ))
            else:
                out.append(Suggestion(
                    category="convergence",
                    message=f"Residual field {f!r} did not converge — try more iterations or relax URF",
                    severity="warn",
                ))
        # Gold comparison
        for q in comparison.failing_quantities:
            if q == "__gold_anchor_missing__":
                out.append(Suggestion(
                    category="gold",
                    message="Gold anchor file missing — verify case_id matches a knowledge/gold_standards/*.yaml",
                    severity="error",
                ))
                continue
            qr = next((q2 for q2 in comparison.quantities if q2.name == q), None)
            if qr is None:
                continue
            if qr.relative_error > 0.20:
                out.append(Suggestion(
                    category="mesh",
                    message=(
                        f"Quantity {q!r} off by {qr.relative_error:.1%} — likely under-resolved mesh; "
                        "try mesh_160 or finer"
                    ),
                    severity="warn",
                ))
            elif qr.relative_error > qr.tolerance:
                out.append(Suggestion(
                    category="turbulence_model",
                    message=(
                        f"Quantity {q!r} off by {qr.relative_error:.1%} (tolerance {qr.tolerance:.1%}) — "
                        "check the turbulence model selection (laminar vs SST vs k-epsilon)"
                    ),
                    severity="warn",
                ))
        # Physics pre-flight
        for fail in physics.failures:
            out.append(Suggestion(
                category="physics",
                message=f"Pre-flight physics failed: {fail}",
                severity="error",
            ))
        for warn in physics.warnings:
            out.append(Suggestion(
                category="physics",
                message=f"Pre-flight physics warning: {warn}",
                severity="info",
            ))
        return out
