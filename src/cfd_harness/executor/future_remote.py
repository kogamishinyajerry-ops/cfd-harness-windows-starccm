"""FutureRemoteExecutor · ExecutorMode.FUTURE_REMOTE (skeleton).

A placeholder for a future cloud / remote executor (eg. STAR-CCM+ on
a remote HPC node). Always returns `MODE_NOT_YET_IMPLEMENTED`.

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

__all__ = ["FutureRemoteExecutor"]


class FutureRemoteExecutor(ExecutorAbc):
    """ExecutorMode.FUTURE_REMOTE — stub until a remote backend is wired."""
    MODE: ClassVar[ExecutorMode] = ExecutorMode.FUTURE_REMOTE

    _STUB_NOTE: ClassVar[str] = "future_remote_stub_only"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._STUB_NOTE,),
        )
