"""Tests for the MockExecutor — the V&V smoke path."""
from __future__ import annotations

import pytest

from cfd_harness.executor.base import ExecutorMode, ExecutorStatus
from cfd_harness.executor.mock import MockExecutor
from cfd_harness.models import FlowType, GeometryType, TaskSpec


def test_mock_returns_ok_with_preset(ldc_task_spec):
    """MockExecutor.execute returns OK with the INTERNAL preset."""
    exe = MockExecutor()
    rpt = exe.execute(ldc_task_spec)
    assert rpt.status == ExecutorStatus.OK
    assert rpt.mode == ExecutorMode.MOCK
    assert rpt.execution_result is not None
    assert rpt.execution_result.is_mock is True
    assert rpt.execution_result.success is True
    assert "u_centerline" in rpt.execution_result.key_quantities
    # The §6.1 ceiling note
    assert "mock_executor_no_truth_source" in rpt.notes


def test_mock_external_preset(naca_task_spec):
    """External flow preset is the EXTERNAL one (strouhal_number, etc.)."""
    exe = MockExecutor()
    rpt = exe.execute(naca_task_spec)
    assert rpt.execution_result.key_quantities.get("mock_preset_marker") is True


def test_mock_natural_convection_preset():
    """NATURAL_CONVECTION flow returns the nusselt_number preset."""
    spec = TaskSpec(
        case_id="differential_heated_cavity",
        flow_type=FlowType.NATURAL_CONVECTION,
        geometry_type=GeometryType.SIMPLE_GRID,
        parameters={"Ra": 1e3, "T_hot": 1.0, "T_cold": 0.0},
    )
    rpt = MockExecutor().execute(spec)
    assert "nusselt_number" in rpt.execution_result.key_quantities
    assert rpt.execution_result.key_quantities["mock_preset_marker"] is True


def test_mock_default_preset_for_unknown_flow():
    """Unknown flow_type falls back to INTERNAL preset (defensive)."""
    spec = TaskSpec(
        case_id="mystery",
        flow_type=FlowType.INTERNAL,  # the only one we always have
        geometry_type=GeometryType.SIMPLE_GRID,
    )
    rpt = MockExecutor().execute(spec)
    assert rpt.status == ExecutorStatus.OK
