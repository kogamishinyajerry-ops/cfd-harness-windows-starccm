"""MockExecutor · ExecutorMode.MOCK.

Synthetic executor that bypasses any real solver. Used for tests and
the chief engineer's mock-first smoke loop. Per EXECUTOR_ABSTRACTION
§6.1, MOCK's TrustGate verdict ceiling is `WARN` (never `PASS`),
with note `mock_executor_no_truth_source`.

Plane: EXECUTION (same as `base.py`).
"""
from __future__ import annotations

from typing import ClassVar, Dict

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from cfd_harness.models import ExecutionResult, FlowType, TaskSpec

__all__ = ["MockExecutor"]


# Per-flow-type synthetic presets. Values are deliberately non-physical —
# they signal "synthetic" in any audit report that compares them against
# gold standards (combined with `is_mock=True` and the
# `mock_executor_no_truth_source` note).
_PRESETS: Dict[str, Dict[str, object]] = {
    "internal": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0],
            "mock_preset_marker": True,
        },
    },
    "external": {
        "residuals": {"p": 1e-5, "U": 1e-5},
        "key_quantities": {
            "strouhal_number": 0.165,
            "cd_mean": 1.36,
            "cl_rms": 0.048,
            "mock_preset_marker": True,
        },
    },
    "natural_convection": {
        "residuals": {"p": 1e-6, "T": 1e-7},
        "key_quantities": {
            "nusselt_number": 4.52,
            "mock_preset_marker": True,
        },
    },
}


def _flow_key(task_spec: TaskSpec) -> str:
    flow = task_spec.flow_type
    if isinstance(flow, FlowType):
        return flow.value
    return str(flow).lower()


class MockExecutor(ExecutorAbc):
    """ExecutorMode.MOCK — TrustGate verdict ceiling = WARN (never PASS).

    The `mock_executor_no_truth_source` note is attached to every
    RunReport this class produces, so downstream TrustGate routing per
    EXECUTOR_ABSTRACTION §6.1 can apply the WARN ceiling without
    special-casing.
    """
    MODE: ClassVar[ExecutorMode] = ExecutorMode.MOCK

    _CEILING_NOTE: ClassVar[str] = "mock_executor_no_truth_source"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        preset = _PRESETS.get(_flow_key(task_spec), _PRESETS["internal"])
        execution = ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),  # type: ignore[arg-type]
            key_quantities=dict(preset["key_quantities"]),  # type: ignore[arg-type]
            execution_time_s=0.01,
            raw_output_path=None,
        )
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=execution,
            notes=(self._CEILING_NOTE,),
        )
