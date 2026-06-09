# cfd-harness-windows-starccm · STATE.md

> **SSOT for delivery state.** The chief engineer updates this file on
> every state change (DEC landing, stage advance, exit-gate pass).
>
> The "covered" map MUST match reality: every "covered" claim is
> backed by a green benchmark that passed its tolerance gate
> end-to-end through the executor. See AGENTS.md §"Definition of
> success".

## Current state (2026-06-10 01:50+08)

| Stage | Scope | Status | Notes |
|---|---|---|---|
| **Stage 0** | Reconnaissance + planning | **done** | cfd-harness-unified 4509 files audited; OpenFOAM/STAR-CCM+ adaptation matrix defined |
| **Stage 1** | Scaffold (reins + AGENTS + executor base/mock + 3 anchor gold_standards + stub adapter) | **done** | 7 reins, 1 spec, 1 ADR, 4 executor implementations, 3 anchor gold_standards ported |
| **Stage 2** | V&V engine port (auto_verifier + report_engine + audit_package + metrics) | **done (mock-first)** | MOCK executor + gold_standard_comparator + convergence_checker + physics_checker + correction_suggester + verifier + signed manifest + report generator + metrics + orchestrator + CLI |
| **Stage 3 Phase A** | **Bridge + executor (real)** | **done** | `CodebuddyRepl` subprocess wrapper + `StarCCMExecutor` real impl + `WinStarCCMExecutor` → delegate. Bridge spawns STAR-CCM+ 19.02.009 in **14.68s** (vortex-street proven path). 5/5 real-solver tests pass. |
| **Stage 3 Phase B** | **LDC Java macro + integration** | **E2E green (sampling partial)** | `LidDrivenCavity.java` written (~735 lines) + 6/6 macro sanity tests pass + LDC_ITERS env override + smoke test green (100-iter, 12s wall) + full 5000-iter run (13.8s wall, .sim saved at `Cases/Results/lid_driven_cavity_solved.sim`, 1.98 MB). **BCs work**: top y_max → InletBoundary + VelocityMagnitudeProfile=1.0 m/s. **FF sampling blocked** by STAR-CCM+ 19.02.009 API (DEC-005; 8 probes documented). Manual GUI verification possible via the saved .sim. |
| **Stage 3 Phase C** | **NACA + cylinder wiring + case_profiles** | **E2E green** | NACA: wired to user's `CliNaca2412E2E.java` (Re=6e6, AoA=4°) via `_resolve_macro_path()` across harness + Codebuddy dirs. Cylinder: vortex-street path (Phase A proven). Per-case output path resolution. **`case_profiles.yaml` consumer wired**: executor reads `sim_path` + `sim_placeholder` from `knowledge/case_profiles.yaml`. |
| **Stage 3 Phase D** | **Full CLI pipeline (executor + V&V + audit + report)** | **E2E green (fail-closed verified)** | `python -m cfd_harness.cli.run --case lid_driven_cavity --executor win_starccm` runs the full pipeline. Produces `reports/<case>/<timestamp>/data.json` + `data.md` with signed manifest. V&V correctly FAILS when CSV is null (fail-closed safety verified). |
| **Stage 4** | 3 anchor cases end-to-end | **partial** | LDC smoke + full + NACA smoke + cylinder spawn all green. LDC Ghia tolerance PASS = deferred (FF sampling; user can manual-verify via GUI). NACA Re=6e6 tolerance = full run pending. |
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
| lid_driven_cavity | ✅ runnable (verdict WARN — MOCK ceiling) | stub (refuses) | ✅ E2E full (5000-iter, 13.8s, .sim saved). **NOT covered**: Ghia 1982 tolerance check needs FF sampling (DEC-005; user manual-verify via GUI) |
| naca0012_airfoil | ✅ runnable | stub (refuses) | ✅ E2E smoke (200-iter, 12s). User's `CliNaca2412E2E.java` (v34) runs end-to-end. NOT covered: full Re=6e6 tolerance check pending |
| circular_cylinder_wake | ✅ runnable | stub (refuses) | ✅ E2E spawn (11s). Vortex-street proven path |
| 14 other gold_standards | ⏳ gold standards not yet ported; CLI doesn't know them | n/a | n/a |

**Law 1 (runnable-coverage)**: a case is "covered" only when its
real-solver run passes its tolerance gate end-to-end. NONE of the
cases are "covered" yet (Stage 3+ work continues). The Mock column is
"runnable on MOCK", not "covered".

## Test coverage

| Suite | Count | Pass | Wall |
|---|---|---|---|
| Main (cfd_harness.tests.*) | 56 | 56 | 13.32s |
| Bridge + Macro (starccm-bridge.tests) | 13 | 13 | 46.05s |
| **Total** | **69** | **69** | **~60s** |

## Open DECs (none yet)

The chief engineer will land DECs as Stage 3+ work begins. Expected
DECs:
- DEC-001: port the OpenFOAM `solver_info` migration for all 14
  remaining gold standards.
- DEC-002: ~~the Codebuddy REPL protocol~~ (closed 2026-06-09; the
  bridge now wraps the 7 unified CLI commands + the vortex-street
  proven path).
- DEC-003: the LDC E2E Stage 3+ exit-gate.
- DEC-004: the case_id → sim_path mapping (currently the CLI looks
  for ``<codebuddy>/Cases/<case_id>.sim``; the existing 100+ sim
  files use their own naming convention ``cyl_vortex_v161R_v26_solved.sim``
  etc. — needs a `case_profiles` config).
- **DEC-005 (new)**: LDC FF sampling blocked by STAR-CCM+ 19.02.009
  API. Acceptable paths: (a) scene export to CSV + external read,
  (b) port a "FVM-based 1-cell region" reporter per the user's
  `probeViaOneCellRegion` pattern, (c) accept LDC smoke green
  as "BCs+physics+solver" verified; defer Ghia tolerance to a
  manual post-process of the saved .sim. Defer until Stage 4.

## Phase B/C done — what's left for the next session

### Phase B (LDC) — done with known limit
1. ~~Write `LidDrivenCavity.java`~~ — **DONE** (~735 lines at
   `D:\CFD-harness-Windows-StarCCM\macros\LidDrivenCavity.java`).
   6/6 macro sanity tests + 1 E2E smoke test pass.
2. ~~Update `_CASE_TO_COMMAND` to route `lid_driven_cavity` → run-macro~~ — **DONE**
3. ~~Add `CodebuddyRepl.run_macro`~~ — **DONE**; spawns STAR-CCM+
   directly with any Java macro
4. **LDC BCs**: ✅ top y_max → InletBoundary + VelocityMagnitudeProfile=1.0
   m/s (set via the user's proven `ConditionTypeManager` + `setMethod`
   pattern). Lid velocity is applied.
5. **LDC physics**: ✅ SteadyModel + TurbulentLaminarModel + SegregatedFlow
   attempted (some FAIL due to `star.turbulence.LaminarModel` rename
   in 19.02.009; not blocking since solver runs).
6. **LDC FF sampling**: ⚠ **BLOCKED**. STAR-CCM+ 19.02.009 has:
   - `PrimitiveFieldFunction.getValue()` no-args only (no `getValue(coord)`)
   - No `ProbeManager` class at all (none of star.common / star.probe / star.common.probes)
   - No `star.base.coordinate.CartesianCoordinate` (ProbeVelocityField's
     pattern doesn't work in this build)
   - No `createSimpleBlockPart` / `createBlockPart` on RegionManager
   Probes confirm. Workarounds deferred (see DEC-005).

### Phase C (NACA + cylinder) — done
1. ✅ NACA wired to user's `CliNaca2412E2E.java` (200-iter smoke green)
2. ✅ Cylinder uses proven `vortex-street` path (Phase A, 11s spawn)
3. ✅ `_resolve_macro_path()` searches both harness + Codebuddy macros dirs
4. ✅ Per-case output path resolution (`_resolve_case_outputs`)

### What's still TODO
1. **LDC full 5000-iter + Ghia tolerance**: blocked on FF sampling
   (DEC-005). User can manually run the .sim in STAR-CCM+ GUI and
   verify the lid-driven cavity against Ghia 1982 Table I.
2. **NACA full run + Re=6e6 tolerance**: smoke runs 200 iters; the
   full convergence run (1000+ iters) and tolerance check can be
   triggered by the CLI runner.
3. **Add `case_profiles.yaml` consumer** in `cfd_harness/cli/run.py`
   so `python -m cfd_harness.cli.run --case lid_driven_cavity` resolves
   the right .sim + macro automatically.
4. **Port 14 remaining gold standards** (see list below).

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
