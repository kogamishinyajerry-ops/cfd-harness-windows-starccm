"""Tests for the executor base + mock + skeleton executors.

Solver-agnostic. The MOCK executor must work on a fresh venv without
`starccm_adapter` importable — this is the mock-first invariant.
"""
from __future__ import annotations

import pytest

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
    SPEC_VERSION,
)
from cfd_harness.executor.docker_openfoam import DockerOpenFOAMExecutor
from cfd_harness.executor.future_remote import FutureRemoteExecutor
from cfd_harness.executor.hybrid_init import HybridInitExecutor
from cfd_harness.executor.mock import MockExecutor
from cfd_harness.executor.win_starccm import WinStarCCMExecutor


def test_executor_mode_str_enum():
    """ExecutorMode values are lowercase strings per the spec."""
    assert ExecutorMode.MOCK == "mock"
    assert ExecutorMode.DOCKER_OPENFOAM == "docker_openfoam"
    assert ExecutorMode.WIN_STARCCM == "win_starccm"
    assert ExecutorMode.HYBRID_INIT == "hybrid_init"
    assert ExecutorMode.FUTURE_REMOTE == "future_remote"
    assert len(list(ExecutorMode)) == 5, "spec v0.3 has 5 modes"


def test_spec_version_is_0_3():
    assert SPEC_VERSION == "0.3"


def test_mock_executor_class_attributes():
    assert MockExecutor.MODE == ExecutorMode.MOCK
    assert MockExecutor.VERSION == SPEC_VERSION


def test_win_starccm_executor_class_attributes():
    assert WinStarCCMExecutor.MODE == ExecutorMode.WIN_STARCCM
    assert WinStarCCMExecutor.VERSION == SPEC_VERSION


def test_docker_openfoam_executor_class_attributes():
    assert DockerOpenFOAMExecutor.MODE == ExecutorMode.DOCKER_OPENFOAM


def test_hybrid_init_executor_class_attributes():
    assert HybridInitExecutor.MODE == ExecutorMode.HYBRID_INIT


def test_future_remote_executor_class_attributes():
    assert FutureRemoteExecutor.MODE == ExecutorMode.FUTURE_REMOTE


def test_contract_hash_is_per_mode_and_spec():
    """contract_hash differs per ExecutorMode (per spec §3) and is stable
    across instances of the same class."""
    mock_a = MockExecutor()
    mock_b = MockExecutor()
    starccm = WinStarCCMExecutor()
    assert mock_a.contract_hash == mock_b.contract_hash
    assert mock_a.contract_hash != starccm.contract_hash


def test_subclass_without_mode_raises():
    """Subclasses MUST declare MODE — TypeError otherwise."""
    with pytest.raises(TypeError):
        class BadExecutor(ExecutorAbc):
            def execute(self, task_spec): ...
        BadExecutor()


def test_run_report_requires_execution_result_for_ok():
    """RunReport(status=OK, execution_result=None) MUST raise ValueError."""
    with pytest.raises(ValueError, match="OK.*requires a populated"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.OK,
            contract_hash="x",
            version="0.3",
            execution_result=None,
        )


def test_run_report_rejects_execution_result_for_refusal():
    """RunReport(status=NOT_YET_IMPLEMENTED, execution_result=...) MUST raise."""
    from cfd_harness.models import ExecutionResult
    with pytest.raises(ValueError, match="must have execution_result=None"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash="x",
            version="0.3",
            execution_result=ExecutionResult(success=True, is_mock=True),
        )


def test_run_report_rejects_bare_string_notes():
    """Notes must be a tuple, not a bare str ('h','i' char-explosion guard)."""
    with pytest.raises(TypeError, match="bare str"):
        RunReport(
            mode=ExecutorMode.MOCK,
            status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
            contract_hash="x",
            version="0.3",
            execution_result=None,
            notes="mock_executor_no_truth_source",  # BUG: bare str
        )


def test_run_report_accepts_single_note_tuple():
    """`notes=("only_one",)` is fine."""
    r = RunReport(
        mode=ExecutorMode.MOCK,
        status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
        contract_hash="x",
        version="0.3",
        execution_result=None,
        notes=("only_one",),
    )
    assert r.notes == ("only_one",)
