"""HybridInitExecutor · ExecutorMode.HYBRID_INIT (skeleton).

Per the original spec: hybrid_init is a "warm-start" mode that copies
the boundary conditions + mesh from a reference run. Until a reference
`docker_openfoam` run anchors the case, hybrid_init MUST refuse with
`MODE_NOT_APPLICABLE` and the `hybrid_init_invariant_unverified` note.

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

__all__ = ["HybridInitExecutor"]


class HybridInitExecutor(ExecutorAbc):
    """ExecutorMode.HYBRID_INIT — anchor-required warm-start mode."""
    MODE: ClassVar[ExecutorMode] = ExecutorMode.HYBRID_INIT

    _ANCHOR_NOTE: ClassVar[str] = "hybrid_init_invariant_unverified"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        # Stage 1+2: always refuse. Real impl in a future Stage
        # will check the case_profile for an anchor run and either
        # warm-start (return OK) or refuse with this note.
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_APPLICABLE,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._ANCHOR_NOTE,),
        )
