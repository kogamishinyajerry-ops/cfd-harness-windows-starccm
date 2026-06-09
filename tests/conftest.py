"""Shared pytest fixtures for cfd-harness-windows-starccm.

This conftest is solver-agnostic — it MUST NOT import from
`cfd_harness.starccm_adapter` (Stage 3+). All real-solver tests must
opt in via `@pytest.mark.real_solver`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_harness.executor.base import ExecutorMode
from cfd_harness.executor.mock import MockExecutor
from cfd_harness.models import FlowType, GeometryType, TaskSpec


@pytest.fixture
def repo_root() -> Path:
    """The repository root."""
    return Path(__file__).resolve().parent.parent


@pytest.fixture
def gold_root(repo_root: Path) -> Path:
    """The `knowledge/gold_standards/` directory."""
    return repo_root / "knowledge" / "gold_standards"


@pytest.fixture
def thresholds_path(repo_root: Path) -> Path:
    """The `knowledge/attestor_thresholds.yaml` file."""
    return repo_root / "knowledge" / "attestor_thresholds.yaml"


@pytest.fixture
def mock_executor() -> MockExecutor:
    """A fresh MockExecutor for tests."""
    return MockExecutor()


@pytest.fixture
def ldc_task_spec(repo_root: Path) -> TaskSpec:
    """A TaskSpec for the lid-driven cavity case (Re=100)."""
    return TaskSpec(
        case_id="lid_driven_cavity",
        flow_type=FlowType.INTERNAL,
        geometry_type=GeometryType.SIMPLE_GRID,
        parameters={"Re": 100, "boundary_conditions": {"top_wall_u": 1.0, "other_walls_u": 0.0}},
        gold_anchor=str(repo_root / "knowledge" / "gold_standards" / "lid_driven_cavity.yaml"),
        solver_profile="",
        mesh_density="default",
    )


@pytest.fixture
def naca_task_spec(repo_root: Path) -> TaskSpec:
    """A TaskSpec for the NACA 0012 case (Re=6e6, alpha=2)."""
    return TaskSpec(
        case_id="naca0012_airfoil",
        flow_type=FlowType.EXTERNAL,
        geometry_type=GeometryType.IMPORTED_GEOMETRY,
        parameters={"Re": 6.0e6, "alpha": 2.0, "Mach": 0.15},
        gold_anchor=str(repo_root / "knowledge" / "gold_standards" / "naca0012_airfoil.yaml"),
        solver_profile="",
        mesh_density="default",
    )


@pytest.fixture
def cylinder_task_spec(repo_root: Path) -> TaskSpec:
    """A TaskSpec for the circular cylinder wake case (Re=200)."""
    return TaskSpec(
        case_id="circular_cylinder_wake",
        flow_type=FlowType.EXTERNAL,
        geometry_type=GeometryType.SIMPLE_GRID,
        parameters={"Re": 200, "diameter": 1.0, "freestream_u": 1.0},
        gold_anchor=str(repo_root / "knowledge" / "gold_standards" / "circular_cylinder_wake.yaml"),
        solver_profile="",
        mesh_density="default",
    )


@pytest.fixture
def hmac_key() -> bytes:
    """A deterministic HMAC key for tests."""
    return b"test-only-do-not-use-in-prod-12345"
