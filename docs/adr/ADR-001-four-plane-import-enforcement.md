# ADR-001: Four-Plane Import Enforcement

> **Status**: Accepted (2026-06-09)
> **Adapted from**: cfd-harness-unified `docs/adr/ADR-001-four-plane-import-enforcement.md`

## Context

The cfd-harness-windows-starccm codebase has both **solver-agnostic**
(V&V engine, audit, metrics) and **solver-specific** (STAR-CCM+ adapter,
Codebuddy bridge) modules. If solver-specific imports leak into
solver-agnostic modules, the abstraction breaks — any change to the
solver side cascades into the V&V side, and the MOCK executor can no
longer be runnable without STAR-CCM+ installed.

## Decision

Every Python module in `cfd_harness/` MUST be assigned to exactly one
**plane** (an architectural layer). Cross-plane imports are forbidden.

## The four planes

| Plane | Path | Direction | Owns |
|---|---|---|---|
| `EXECUTION` | `cfd_harness.executor` | downstream | `ExecutorAbc`, `ExecutorMode`, `RunReport`, executors |
| `VERIFICATION` | `cfd_harness.auto_verifier` | downstream | gold comparator, convergence checker, physics checker |
| `REPORTING` | `cfd_harness.report_engine` | downstream | data collector, generator, contract dashboard |
| `AUDIT` | `cfd_harness.audit_package` | downstream | signed manifest, serialization, signing |
| `METRICS` | `cfd_harness.metrics` | downstream | V&V metrics |
| `ADAPTER_STARCCM` | `cfd_harness.starccm_adapter` | downstream | STAR-CCM+ adapter (Stage 3+) |
| `ADAPTER_STARCCM` | `packages/starccm-bridge` | downstream | Codebuddy REPL bridge (separate sub-package) |

The direction is **downstream**: higher-numbered planes (ADAPTER_STARCCM)
import from lower-numbered planes (EXECUTION), not vice versa.

## Enforcement

- **Static**: `import-linter` rules in `pyproject.toml` enforce
  the dependency direction. The contract is:
  - `EXECUTION` has no cross-plane imports.
  - `VERIFICATION` MAY import from `EXECUTION` only.
  - `REPORTING` MAY import from `EXECUTION` and `VERIFICATION`.
  - `AUDIT` MAY import from `EXECUTION`, `VERIFICATION`, `REPORTING`, `METRICS`.
  - `ADAPTER_STARCCM` MAY import from all of the above; downstream
    planes MUST NOT import from `ADAPTER_STARCCM`.
- **CI**: `pytest tests/test_plane_enforcement.py` runs in CI; it
  walks the AST of every module and fails if a forbidden cross-plane
  import is found.
- **Pre-commit**: `import-linter` runs on every commit; failures block
  the commit.

## Consequences

- STAR-CCM+-specific imports (`from cfd_harness.starccm_adapter import ...`)
  MUST stay within `ADAPTER_STARCCM` plane modules and any tests marked
  `@pytest.mark.real_solver`.
- The `MOCK` executor (`cfd_harness.executor.mock.MockExecutor`) MUST
  be importable without `starccm_adapter` being importable — a
  test that loads `MockExecutor` on a fresh venv (no
  `starccm_adapter` installed) MUST pass.
- Adding a new solver adapter (eg. `WIN_FLUENT`) means a new plane
  `ADAPTER_FLUENT` with the same rules.

## Reference impl

- `cfd_harness.executor.base` — `Plane.EXECUTION` (lowest plane in
  the solver-agnostic engine).
- `cfd_harness.starccm_adapter` — `Plane.ADAPTER_STARCCM` (Stage 3+).
- `tests/test_plane_enforcement.py` — AST-walking test (Stage 1+).
