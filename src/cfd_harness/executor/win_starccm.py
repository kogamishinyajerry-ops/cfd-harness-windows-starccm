"""WinStarCCMExecutor · ExecutorMode.WIN_STARCCM (Stage 1+2 stub).

In Stage 1+2, this is a stub returning `MODE_NOT_YET_IMPLEMENTED`. In
Stage 3+, the real impl wraps `packages.starccm_bridge.CodebuddyRepl`
which subprocesses the user's existing
`D:\StarCCM Codebuddy\starccm_cli_repl.py`.

The trust-core separation is strict: the real WinStarCCMExecutor
imports `cfd_harness.starccm_adapter.*` only inside `execute()` (lazy
import), so the EXECUTION plane itself stays solver-agnostic and the
test path with MOCK executor works on a fresh venv without
`starccm_adapter` importable.

Plane: EXECUTION. The actual STAR-CCM+-specific code lives in the
`ADAPTER_STARCCM` plane (`cfd_harness.starccm_adapter` and
`packages.starccm_bridge`).
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

__all__ = ["WinStarCCMExecutor"]


class WinStarCCMExecutor(ExecutorAbc):
    """ExecutorMode.WIN_STARCCM — full triad verdict surface (Stage 3+)."""
    MODE: ClassVar[ExecutorMode] = ExecutorMode.WIN_STARCCM

    _STUB_NOTE: ClassVar[str] = "win_starccm_stub_stage1plus2"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        # Stage 1+2: refuse; return MODE_NOT_YET_IMPLEMENTED with a
        # diagnostic note. Real impl lands in Stage 3+ — at that point
        # `execute()` will lazily import from
        # `cfd_harness.starccm_adapter.executor.StarCCMExecutor` (the
        # ADAPTER_STARCCM plane).
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=None,
            notes=(self._STUB_NOTE,),
        )
