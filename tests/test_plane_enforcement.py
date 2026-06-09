r"""Four-plane import law enforcement (ADR-001).

The chief engineer / system-architect rely on this test to catch any
solver-specific import that leaks into a solver-agnostic plane.

Plane assignment:
  - EXECUTION:    cfd_harness.executor
  - VERIFICATION: cfd_harness.auto_verifier
  - REPORTING:    cfd_harness.report_engine
  - AUDIT:        cfd_harness.audit_package
  - METRICS:      cfd_harness.metrics
  - ADAPTER_STARCCM: cfd_harness.starccm_adapter, packages.starccm_bridge

Forbidden cross-plane imports:
  - EXECUTION must NOT import from VERIFICATION / REPORTING / AUDIT / METRICS / ADAPTER_*
  - VERIFICATION must NOT import from REPORTING / AUDIT / METRICS / ADAPTER_*
  - REPORTING must NOT import from AUDIT / METRICS / ADAPTER_*
  - AUDIT must NOT import from ADAPTER_*
  - ADAPTER_* must NOT be imported by the solver-agnostic planes

The ``import-linter`` tool in pyproject.toml enforces this in CI. This
test is the lightweight AST-walking fallback that runs in the unit
test suite (and on a fresh venv).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src" / "cfd_harness"


# Plane -> package paths under src/cfd_harness
PLANES = {
    "EXECUTION":     "executor",
    "VERIFICATION":  "auto_verifier",
    "REPORTING":     "report_engine",
    "AUDIT":         "audit_package",
    "METRICS":       "metrics",
    "ADAPTER_STARCCM": "starccm_adapter",
}

# Forbidden import directions (per ADR-001).
# Format: source_plane -> set of forbidden_target_planes
FORBIDDEN = {
    "EXECUTION":     {"VERIFICATION", "REPORTING", "AUDIT", "METRICS", "ADAPTER_STARCCM"},
    "VERIFICATION":  {"REPORTING", "AUDIT", "METRICS", "ADAPTER_STARCCM"},
    "REPORTING":     {"AUDIT", "METRICS", "ADAPTER_STARCCM"},
    "AUDIT":         {"ADAPTER_STARCCM"},
    "METRICS":       {"ADAPTER_STARCCM"},
    "ADAPTER_STARCCM": set(),   # downstream — can import from all upstream
}


def _walk_imports(py_path: Path) -> list[str]:
    """Walk a Python file and yield the module names it imports."""
    try:
        tree = ast.parse(py_path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                out.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                out.append(node.module)
                # also resolve the level
                for alias in node.names:
                    full = f"{node.module}.{alias.name}" if node.module else alias.name
                    out.append(full)
    return out


def _plane_of_import(import_name: str) -> str | None:
    """Map an import name to its plane (or None if outside cfd_harness)."""
    if not import_name.startswith("cfd_harness"):
        return None
    # find the next part after 'cfd_harness'
    parts = import_name.split(".")
    if len(parts) < 2:
        return None
    candidate = parts[1]
    for plane, pkg in PLANES.items():
        if candidate == pkg:
            return plane
    return None


@pytest.mark.parametrize("plane", list(PLANES.keys()))
def test_no_forbidden_cross_plane_imports(plane):
    """No file in the plane may import from a forbidden plane."""
    pkg_dir = SRC_ROOT / PLANES[plane]
    if not pkg_dir.exists():
        pytest.skip(f"plane dir missing: {pkg_dir}")
    forbidden_targets = FORBIDDEN[plane]
    violations: list[tuple[Path, str]] = []
    for py in pkg_dir.rglob("*.py"):
        for imp in _walk_imports(py):
            target_plane = _plane_of_import(imp)
            if target_plane is None:
                continue
            if target_plane in forbidden_targets:
                # Relativize the import for a clearer error.
                violations.append((py.relative_to(REPO_ROOT), imp))
    assert not violations, (
        f"Plane {plane!r} has forbidden cross-plane imports:\n"
        + "\n".join(f"  {p}: {imp}" for p, imp in violations)
    )


def test_executor_does_not_import_starccm_adapter():
    """The MOCK-first invariant: the EXECUTION plane must NOT
    statically import from the ADAPTER_STARCCM plane. The real
    `WinStarCCMExecutor.execute` is allowed to lazily import at
    runtime (Stage 3+), but the static AST must be clean.
    """
    executor_dir = SRC_ROOT / "executor"
    for py in executor_dir.rglob("*.py"):
        for imp in _walk_imports(py):
            if imp.startswith("cfd_harness.starccm_adapter"):
                pytest.fail(
                    f"{py.relative_to(REPO_ROOT)} statically imports {imp!r}; "
                    "the EXECUTION plane must not import from ADAPTER_STARCCM"
                )


def test_starccm_adapter_does_not_import_cli():
    """The ADAPTER_STARCCM plane is downstream of the CLI plane; this
    is a reverse-direction guard, not strictly required by ADR-001
    (CLI is not a plane in the formal list), but it's a useful
    hygiene check that the adapter stays solver-only."""
    adapter_dir = SRC_ROOT / "starccm_adapter"
    if not adapter_dir.exists():
        pytest.skip("starccm_adapter not present")
    for py in adapter_dir.rglob("*.py"):
        for imp in _walk_imports(py):
            if imp.startswith("cfd_harness.cli"):
                pytest.fail(
                    f"{py.relative_to(REPO_ROOT)} imports {imp!r}; "
                    "ADAPTER_STARCCM must not import from CLI"
                )
