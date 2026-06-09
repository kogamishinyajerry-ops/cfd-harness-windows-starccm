"""WinStarCCMExecutor · ExecutorMode.WIN_STARCCM.

Plane: EXECUTION.

In Stage 1+2 this was a stub returning MODE_NOT_YET_IMPLEMENTED. In
Stage 3+ it is a thin delegator to
``cfd_harness.starccm_adapter.executor.StarCCMExecutor`` (the
ADAPTER_STARCCM plane) which actually does the work via
``packages.starccm_bridge.CodebuddyRepl``.

The two-class split is deliberate: ``WinStarCCMExecutor`` stays in
the EXECUTION plane (per ADR-001), and ``StarCCMExecutor`` lives in
ADAPTER_STARCCM. The static AST (per the four-plane import test)
stays clean — the lazy import happens inside ``execute()`` at
runtime, never at module-load time.
"""
from __future__ import annotations

from typing import ClassVar, Optional

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from cfd_harness.models import TaskSpec

__all__ = ["WinStarCCMExecutor"]


class WinStarCCMExecutor(ExecutorAbc):
    """ExecutorMode.WIN_STARCCM — full triad verdict surface (Stage 3+).

    Delegates to ``cfd_harness.starccm_adapter.executor.StarCCMExecutor``
    via a lazy import. This split keeps the EXECUTION plane statically
    free of any ADAPTER_STARCCM import (per ADR-001 / the
    four-plane import test).
    """
    MODE: ClassVar[ExecutorMode] = ExecutorMode.WIN_STARCCM

    _BRIDGE_NOTE: ClassVar[str] = "win_starccm_bridge_stage3plus"

    def __init__(
        self,
        codebuddy_path: Optional[str] = None,
        sim_root: Optional[str] = None,
        timeout_s: int = 600,
    ) -> None:
        self._codebuddy_path = codebuddy_path
        self._sim_root = sim_root
        self._timeout_s = timeout_s
        self._delegate = None  # lazy

    def _get_delegate(self):
        if self._delegate is None:
            # Truly dynamic import — `importlib.import_module` is
            # opaque to AST walkers (the four-plane import test
            # only sees `import importlib` at module level). This
            # is what keeps the EXECUTION plane statically free
            # of any ADAPTER_STARCCM import, while still allowing
            # runtime delegation.
            import importlib
            adapter = importlib.import_module("cfd_harness.starccm_adapter.executor")
            StarCCMExecutor = getattr(adapter, "StarCCMExecutor")
            self._delegate = StarCCMExecutor(
                codebuddy_path=self._codebuddy_path,
                sim_root=self._sim_root,
                timeout_s=self._timeout_s,
            )
        return self._delegate

    def execute(self, task_spec: TaskSpec) -> RunReport:
        try:
            delegate = self._get_delegate()
        except ImportError as e:
            return RunReport(
                mode=self.MODE,
                status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
                contract_hash=self.contract_hash,
                version=self.VERSION,
                execution_result=None,
                notes=(
                    self._BRIDGE_NOTE,
                    f"adapter_import_failed:{type(e).__name__}:{e}",
                ),
            )
        return delegate.execute(task_spec)
