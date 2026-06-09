"""ConvergenceChecker: verifies the solver's residuals have converged.

Solver-agnostic. Operates on a dict of `residual_field -> final_value`
(eg. `{"p": 1e-6, "U": 1e-6, "T": 1e-7}`).

The check is a simple "all residuals below the floor" gate. Stage 3+
may add a per-field residual series check (need the full time/iter
series from the solver log), but for the gold-comparator v0, a final
value below the floor is sufficient.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

__all__ = ["ConvergenceChecker", "ConvergenceResult"]


@dataclass(frozen=True)
class ConvergenceResult:
    """Outcome of a single convergence check.

    `all_pass=True` iff every residual field is below the floor.
    `failing_fields` lists the names of fields that failed.
    """
    all_pass: bool
    failing_fields: List[str]

    def __bool__(self) -> bool:  # truthy iff all_pass
        return self.all_pass


class ConvergenceChecker:
    """Residual convergence gate.

    `residual_floor`: the largest acceptable final residual. The
    per-case override (via `VerifierConfig.for_case`) is plumbed in
    by the caller.
    """
    def __init__(self, residual_floor: float) -> None:
        if residual_floor <= 0:
            raise ValueError(f"residual_floor must be > 0, got {residual_floor}")
        self.residual_floor = residual_floor

    def check(self, residuals: Dict[str, float]) -> ConvergenceResult:
        if not residuals:
            return ConvergenceResult(all_pass=False, failing_fields=["__no_residuals__"])
        failing = [
            name for name, value in residuals.items()
            if value is None or value > self.residual_floor
        ]
        return ConvergenceResult(
            all_pass=len(failing) == 0,
            failing_fields=failing,
        )
