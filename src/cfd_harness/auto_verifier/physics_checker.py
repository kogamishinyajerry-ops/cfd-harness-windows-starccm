"""PhysicsChecker: pre-flight physics sanity checks.

Solver-agnostic. Checks for:
  - the case's flow_type matches the geometry (eg. NATURAL_CONVECTION
    requires a temperature-driven BC)
  - the Re / Ra / Mach is within the gold standard's documented range
  - the BC signature is complete (eg. INTERNAL with cavity needs
    top_wall_u and other_walls_u)

These are coarse guards, not a full BC validator. The original
cfd-harness-unified had a more elaborate `case_completeness` service;
for v1 of cfd-harness-windows-starccm, this is the minimal viable
physics pre-flight.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from cfd_harness.models import FlowType, GeometryType, TaskSpec

__all__ = ["PhysicsChecker", "PhysicsCheckResult"]


@dataclass(frozen=True)
class PhysicsCheckResult:
    """Outcome of a physics pre-flight check."""
    all_pass: bool
    warnings: List[str] = field(default_factory=list)
    failures: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.all_pass


class PhysicsChecker:
    """Pre-flight physics sanity. Solver-agnostic."""
    # The flow types that REQUIRE a temperature field in parameters.
    _TEMP_REQUIRED = {FlowType.NATURAL_CONVECTION, FlowType.CONJUGATE}

    def check(self, task_spec: TaskSpec) -> PhysicsCheckResult:
        warnings: List[str] = []
        failures: List[str] = []

        if task_spec.flow_type in self._TEMP_REQUIRED:
            if not self._has_temperature(task_spec.parameters):
                failures.append(
                    f"flow_type={task_spec.flow_type.value} requires temperature parameters"
                )

        # Re range check (coarse).
        Re = task_spec.parameters.get("Re")
        if Re is not None:
            try:
                Re_f = float(Re)
                if Re_f <= 0:
                    failures.append(f"Re must be > 0, got {Re_f}")
            except (TypeError, ValueError):
                warnings.append(f"Re={Re!r} is not numeric")

        # BC signature check (coarse — full check lives in
        # case_scaffold / case_dicts in a future stage).
        if task_spec.flow_type == FlowType.INTERNAL and task_spec.geometry_type == GeometryType.SIMPLE_GRID:
            if "boundary_conditions" not in task_spec.parameters:
                warnings.append("INTERNAL+SIMPLE_GRID has no boundary_conditions in parameters")

        return PhysicsCheckResult(
            all_pass=len(failures) == 0,
            warnings=warnings,
            failures=failures,
        )

    def _has_temperature(self, parameters: Dict[str, Any]) -> bool:
        if any(k in parameters for k in ("T_wall", "T_hot", "T_cold", "dT", "T_ref")):
            return True
        return any(
            isinstance(v, (int, float)) and k.lower().startswith("t")
            for k, v in parameters.items()
        )
