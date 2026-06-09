"""TaskSpec, ExecutionResult, FlowType, GeometryType, CFDExecutor protocol.

solver-agnostic. Imported by every other solver-agnostic module; lives in
the `models` plane (the lowest plane, has no cross-plane imports).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Dict, Optional, Protocol, runtime_checkable


class FlowType(StrEnum):
    """Solver-agnostic flow regime. Maps to solver-specific setup."""
    INTERNAL = "internal"                     # cavity, channel, duct
    EXTERNAL = "external"                     # cylinder wake, airfoil, flat plate
    NATURAL_CONVECTION = "natural_convection" # DHC, Rayleigh-Bénard
    CONJUGATE = "conjugate"                   # CHT (solid + fluid)
    COMPRESSIBLE = "compressible"             # supersonic, shock

    @classmethod
    def from_str(cls, s: str) -> "FlowType":
        # Accept legacy "INTERNAL" / "internal" / "Internal" forms.
        try:
            return cls(s.lower())
        except ValueError:
            return cls(s.upper())


class GeometryType(StrEnum):
    """Solver-agnostic geometry source."""
    SIMPLE_GRID = "simple_grid"               # parametric box/cavity/channel
    IMPORTED_GEOMETRY = "imported_geometry"   # user-provided STL/STEP
    CAD_GEOMETRY = "cad_geometry"             # FreeCAD STEP → STL


@dataclass(frozen=True)
class TaskSpec:
    """The solver-agnostic task description.

    `frozen=True` ensures byte-determinism: a TaskSpec cannot be mutated
    after construction, so any audit-package side logic that hashes or
    serializes it sees a stable shape.
    """
    case_id: str                                # e.g. "lid_driven_cavity"
    flow_type: FlowType
    geometry_type: GeometryType
    parameters: Dict[str, Any] = field(default_factory=dict)
    gold_anchor: str = ""                       # path to knowledge/gold_standards/<id>.yaml
    solver_profile: str = ""                    # path to solver profile yaml
    mesh_density: str = "default"               # "mesh_20" | "mesh_40" | "mesh_80" | "mesh_160"
    timeout_s: int = 3600


@dataclass(frozen=True)
class ExecutionResult:
    """The solver-agnostic execution result.

    `is_mock=True` is a MANDATORY tag for the MOCK executor. Downstream
    code (comparator, audit_package) can use this to gate things
    (eg. don't trust gold-comparator PASS on is_mock=True).
    """
    success: bool
    is_mock: bool
    residuals: Dict[str, float] = field(default_factory=dict)
    key_quantities: Dict[str, Any] = field(default_factory=dict)
    execution_time_s: float = 0.0
    raw_output_path: Optional[Path] = None
    case_manifest_hash: Optional[str] = None

    def __post_init__(self) -> None:
        # Type guards — frozen dataclass cannot stop callers from passing
        # raw strings for is_mock; we normalize here.
        if not isinstance(self.is_mock, bool):
            raise TypeError(
                f"ExecutionResult.is_mock must be bool, got {type(self.is_mock).__name__}"
            )
        if not isinstance(self.success, bool):
            raise TypeError(
                f"ExecutionResult.success must be bool, got {type(self.success).__name__}"
            )


@runtime_checkable
class CFDExecutor(Protocol):
    """Protocol that any solver executor must implement.

    This is solver-agnostic; the concrete implementations live in:
    - `cfd_harness.executor.mock.MockExecutor` (MOCK)
    - `cfd_harness.executor.docker_openfoam.DockerOpenFOAMExecutor` (DOCKER_OPENFOAM)
    - `cfd_harness.starccm_adapter.executor.StarCCMExecutor` (WIN_STARCCM, Stage 3+)
    - `cfd_harness.executor.{hybrid_init,future_remote}.*` (skeleton)
    """
    def execute(self, task_spec: TaskSpec) -> ExecutionResult: ...


__all__ = [
    "FlowType",
    "GeometryType",
    "TaskSpec",
    "ExecutionResult",
    "CFDExecutor",
]
