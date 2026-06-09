# cfd-harness-windows-starccm · STATE.md

> **SSOT for delivery state.** The chief engineer updates this file on
> every state change (DEC landing, stage advance, exit-gate pass).
>
> The "covered" map MUST match reality: every "covered" claim is
> backed by a green benchmark that passed its tolerance gate
> end-to-end through the executor. See AGENTS.md §"Definition of
> success".

## Current state (2026-06-09 22:30+08)

| Stage | Scope | Status | Notes |
|---|---|---|---|
| **Stage 0** | Reconnaissance + planning | **done** | cfd-harness-unified 4509 files audited; OpenFOAM/STAR-CCM+ adaptation matrix defined |
| **Stage 1** | Scaffold (reins + AGENTS + executor base/mock + 3 anchor gold_standards + stub adapter) | **done** | 7 reins, 1 spec, 1 ADR, 4 executor implementations, 3 anchor gold_standards ported |
| **Stage 2** | V&V engine port (auto_verifier + report_engine + audit_package + metrics) | **done (mock-first)** | MOCK executor + gold_standard_comparator + convergence_checker + physics_checker + correction_suggester + verifier + signed manifest + report generator + metrics + orchestrator + CLI |
| **Stage 3** | Real STAR-CCM+ bridge (1 case E2E on WIN_STARCCM) | **not started** | stub executors return MODE_NOT_YET_IMPLEMENTED |
| **Stage 4** | 3 anchor cases (LDC + NACA + cylinder wake) end-to-end | **not started** | depends on Stage 3 |
| **Stage 5+** | UI (FastAPI + React) | **deferred** | headless / agent-driven v1 |

## Stage 1+2 inventory (files written)

| Category | Files | Status |
|---|---|---|
| Top-level | README.md, AGENTS.md, OPENCODE.md, pyproject.toml, .gitignore | done |
| Multi-agent reins | 7 reins in `.harness/reins/*/agent.md` (chief, starccm-adapter, vv-director, system-architect, backend, test-red, docs-knowledge) | done |
| Specs / governance | docs/specs/EXECUTOR_ABSTRACTION.md v0.3, docs/adr/ADR-001-four-plane-import-enforcement.md | done |
| V&V engine | 25 Python files: executor (5) + auto_verifier (8) + report_engine (4) + audit_package (4) + metrics (1) + orchestrator (1) + models (1) + cli (2) | done |
| StarCCM+ stub | src/cfd_harness/starccm_adapter/__init__.py + executor.py | stub (Stage 3+) |
| Codebuddy bridge | packages/starccm-bridge/ pyproject.toml + repl.py | stub (Stage 3+) |
| Knowledge | whitelist.yaml + attestor_thresholds.yaml + skill_index.yaml + README.md + 3 anchor gold_standards (LDC + NACA + cylinder) | done |
| Tests | conftest.py + 7 test files (executor, auto_verifier, audit, plane_enforcement, skill_loader, cli_smoke) | done |

**Mock-first invariant holds**: `pytest -m "not real_solver"` is green
on a fresh venv without `starccm_adapter` importable (well, with the
stub importable — Stage 3+ will lazy-import the real adapter).

## "Covered" map (what's runnable end-to-end)

| Case | Mock | Docker OpenFOAM | WIN_STARCCM |
|---|---|---|---|
| lid_driven_cavity | ✅ runnable (verdict WARN — MOCK ceiling) | stub (refuses) | stub (refuses) |
| naca0012_airfoil | ✅ runnable | stub (refuses) | stub (refuses) |
| circular_cylinder_wake | ✅ runnable | stub (refuses) | stub (refuses) |
| 14 other gold_standards | ⏳ gold standards not yet ported; CLI doesn't know them | n/a | n/a |

**Law 1 (runnable-coverage)**: a case is "covered" only when its
real-solver run passes its tolerance gate end-to-end. NONE of the
cases are "covered" yet (Stage 3+ work). The Mock column is
"runnable on MOCK", not "covered".

## Open DECs (none yet)

The chief engineer will land DECs as Stage 3+ work begins. Expected
DECs:
- DEC-001: port the OpenFOAM `solver_info` migration for all 14
  remaining gold standards.
- DEC-002: the Codebuddy REPL protocol (what commands to send, what
  responses to expect).
- DEC-003: the LDC E2E Stage 3+ exit-gate.

## Open follow-ups

- Port 14 remaining gold standards (`backward_facing_step`,
  `cht_pipe_gnielinski`, `cht_straight_fin`, `cylinder_crossflow`,
  `differential_heated_cavity`, `duct_flow`,
  `fully_developed_plane_channel_flow`, `impinging_jet`,
  `plane_channel_flow`, `rayleigh_benard_convection`,
  `turbulent_flat_plate`, `axisymmetric_impinging_jet`,
  `backward_facing_step_steady`, `lid_driven_cavity_benchmark`).
- Port the test fixtures (8 cases × 7 mesh densities = 56 fixtures
  in cfd-harness-unified). Stage 2 mock-first doesn't need them;
  Stage 3+ may need a few for the V&V comparator.
- The `report_engine.contract_dashboard` and
  `report_engine.visual_acceptance` modules (port from
  cfd-harness-unified, ~95KB combined) — Stage 5+ UI work.
- 14 ADRs (four-plane runtime, byte-determinism, etc.) — Stage 2.5.
- The `ui/` (FastAPI + React) — Stage 5+ deferred per the chief
  engineer's L0 autonomy grant.
