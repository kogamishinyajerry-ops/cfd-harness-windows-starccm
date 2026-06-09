"""StarCCMExecutor: the real STAR-CCM+ adapter (Stage 1+2 stub).

Plane: ADAPTER_STARCCM.

Stage 1+2: this class exists for the import to succeed (and for
the four-plane import law to be testable) but its `execute` method
raises `NotImplementedError` with a clear Stage-3+ message.

Stage 3+ implementation plan:
  1. Import `CodebuddyRepl` from `packages.starccm_bridge`.
  2. The Repl subprocesses `D:\\StarCCM Codebuddy\\starccm_cli_repl.py`
     (the user's existing CLI, 1686 tests).
  3. Generate Java macros for mesh / solve / postprocess (one macro
     per case family; StarCCM's "macro file" workflow).
  4. Parse the .sim log to extract residuals + key_quantities.
  5. Sample at the gold-standard reference points.
  6. Return a populated `ExecutionResult` to the EXECUTION plane.
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

__all__ = ["StarCCMExecutor"]


class StarCCMExecutor(ExecutorAbc):
    """ExecutorMode.WIN_STARCCM — full triad verdict surface (Stage 3+).

    In Stage 1+2, `execute()` raises NotImplementedError with a
    diagnostic message. The execution path is
    `WinStarCCMExecutor.execute → StarCCMExecutor.execute →
    CodebuddyRepl.send_command` (Stage 3+).
    """
    MODE: ClassVar[ExecutorMode] = ExecutorMode.WIN_STARCCM

    _STAGE_NOTE: ClassVar[str] = "starccm_adapter_real_impl_stage_3plus"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        # Stage 1+2: refuse with MODE_NOT_YET_IMPLEMENTED. The real
        # impl will live here in Stage 3+ — it will lazily import
        # CodebuddyRepl from packages.starccm_bridge (the actual
        # STAR-CCM+-specific subprocess wrapper).
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._STAGE_NOTE,),
        )
