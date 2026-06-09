"""DockerOpenFOAMExecutor · ExecutorMode.DOCKER_OPENFOAM (skeleton in v0.1.0).

Stage 1+2: stub — returns `MODE_NOT_YET_IMPLEMENTED`. The real
implementation will wrap the OpenFOAM-in-Docker adapter (a port of
`cfd-harness-unified`'s FoamAgentExecutor); for v1 of
cfd-harness-windows-starccm, the Windows + STAR-CCM+ path is the
priority, so this executor is a placeholder for a future Linux /
Docker-OpenFOAM workflow.

Plane: EXECUTION.
"""
from __future__ import annotations

from typing import ClassVar

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from cfd_harness.models import TaskSpec

__all__ = ["DockerOpenFOAMExecutor"]


class DockerOpenFOAMExecutor(ExecutorAbc):
    """ExecutorMode.DOCKER_OPENFOAM — full triad verdict surface (when real)."""
    MODE: ClassVar[ExecutorMode] = ExecutorMode.DOCKER_OPENFOAM

    _STUB_NOTE: ClassVar[str] = "docker_openfoam_stub_stage1plus2"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        # Stage 1+2: refuse; return MODE_NOT_YET_IMPLEMENTED with a
        # diagnostic note. Real impl lands in a future Stage.
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._STUB_NOTE,),
        )
