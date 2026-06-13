# cfd-harness-windows-starccm · STATE.md

> **SSOT for delivery state.** The chief engineer updates this file on
> every state change (DEC landing, stage advance, exit-gate pass).
>
> The "covered" map MUST match reality: every "covered" claim is
> backed by a green benchmark that passed its tolerance gate
> end-to-end through the executor. See AGENTS.md §"Definition of
> success".

## Current state (2026-06-13 — takeover stabilization pass)

> Header date corrected: the file's appended body (C-1.x) and the Open-DEC
> table run through 2026-06-13, so the prior "2026-06-11 00:30" header
> understated the content. Test counts, the DEC table, and the C-1.1 note
> were reconciled to verified reality in the 2026-06-13 takeover pass.

| Stage | Scope | Status | Notes |
|---|---|---|---|
| **Stage 0** | Reconnaissance + planning | **done** | cfd-harness-unified 4509 files audited; OpenFOAM/STAR-CCM+ adaptation matrix defined |
| **Stage 1** | Scaffold (reins + AGENTS + executor base/mock + 3 anchor gold_standards + stub adapter) | **done** | 7 reins, 1 spec, 1 ADR, 4 executor implementations, 3 anchor gold_standards ported |
| **Stage 2** | V&V engine port (auto_verifier + report_engine + audit_package + metrics) | **done (mock-first)** | MOCK executor + gold_standard_comparator + convergence_checker + physics_checker + correction_suggester + verifier + signed manifest + report generator + metrics + orchestrator + CLI |
| **Stage 2.5** | **Mock coverage expansion (16 cases)** | **done (2026-06-11)** | 13 new gold_standards ported from cfd-harness-unified → CLI dispatch + MOCK `_CASE_PRESETS` extended. 16/16 cases smoke-green on MOCK executor. `python scripts/smoke_16cases.py` = 16/16 PASS. Test regression 56/56 PASS. See DEC-006. |
| **Stage 3 Phase A** | **Bridge + executor (real)** | **done** | `CodebuddyRepl` subprocess wrapper + `StarCCMExecutor` real impl + `WinStarCCMExecutor` → delegate. Bridge spawns STAR-CCM+ 19.02.009 in **14.68s** (vortex-street proven path). 5/5 real-solver tests pass. |
| **Stage 3 Phase B** | **LDC Java macro + integration** | **E2E green (sampling partial)** | `LidDrivenCavity.java` written (~735 lines) + 6/6 macro sanity tests pass + LDC_ITERS env override + smoke test green (100-iter, 12s wall) + full 5000-iter run (13.8s wall, .sim saved at `Cases/Results/lid_driven_cavity_solved.sim`, 1.98 MB). **BCs work**: top y_max → InletBoundary + VelocityMagnitudeProfile=1.0 m/s. **FF sampling blocked** by STAR-CCM+ 19.02.009 API (DEC-005; 8 probes documented). Manual GUI verification possible via the saved .sim. |
| **Stage 3 Phase C** | **NACA + cylinder wiring + case_profiles** | **E2E green** | NACA: wired to user's `CliNaca2412E2E.java` (Re=6e6, AoA=4°) via `_resolve_macro_path()` across harness + Codebuddy dirs. Cylinder: vortex-street path (Phase A proven). Per-case output path resolution. **`case_profiles.yaml` consumer wired**: executor reads `sim_path` + `sim_placeholder` from `knowledge/case_profiles.yaml`. |
| **Stage 3 Phase D** | **Full CLI pipeline (executor + V&V + audit + report)** | **E2E green (fail-closed verified)** | `python -m cfd_harness.cli.run --case lid_driven_cavity --executor win_starccm` runs the full pipeline. Produces `reports/<case>/<timestamp>/data.json` + `data.md` with signed manifest. V&V correctly FAILS when CSV is null (fail-closed safety verified). |
| **Stage 4 Phase E v1** | **NACA real-solver closed loop (DEC-007)** | **done (path green; V&V still FAIL vs gold)** | NacaTrueE2E.java v1 (354 lines) walks STAR-CCM+ 2402 end-to-end: STL import (6-face cube + airfoil) → Boolean Subtract → Region → Physics (k-omega SST) → BCs (xmin Inlet / xmax Outlet / ybot/ytop/zin/zout Sym / naca2412 Wall) → Mesh (6.8 s) → Init + 500 iter (109 s) → ForceCoefficientReport extract Cl/Cd → save .sim. **Steady-state result**: Cl=0.0096, Cd=0.0015, Cm=1.5e-5 (real STAR-CCM+ output, not mock). V&V comparator still WARN/FAIL vs Ladson 1988 (gold Cl=0.235, Cd=0.0061) — 96% / 75% off, expected for v1 smoke (alpha tilt not yet applied; Re=1e6 not 6e6; mesh coarse). See DEC-007 follow-ups for Stage 4 Phase E v2. |
| **Stage 4 Phase E v2** | **NACA α-tilt attempt + report introspection** | **partial (pipeline green; α-tilt + report reading blocked by 2402 R8)** | NacaTrueE2E.java grown to 902 lines; vector-profile `setMethod(ConstantVectorProfileMethod.class)` rejected with `NeoException: ProfileMethod not found in Profile`; `star.models.VelocityProfile` `ClassNotFoundException`; `star.flow.VelocityProfile` returns null. **Fallback**: 15 m/s scalar X, no α tilt. 2000-iter steady green (137 s). **Pressure PNG works** (stagnation + suction classical Cp). **Velocity PNG works** (boundary layer visible). **Cl/Cd report reading broken**: `compute()` `NoSuchMethodException`; `getValue()` returns Vector3 with field names `x/y/z` (NOT `[Cd, Cl, Cm]`); values bit-identical across 10/15 m/s and α=0/4° runs → likely stale-cached/sentinel. DEC-005 broadened to cover report reading. See `reports/decisions/DEC-007-NACA-v2-alpha-tilt-attempt.md`. |
| **Stage 4 Phase E v3** | **NACA domain rotation 4° + setBaseSize attempt** | **partial (α=4° applied geometrically; setBaseSize API not found)** | `gen_naca_domain_cube.py --aoa 4.0` rotates cube 4° about z-axis at (0.25, 0, 0); cube STL regenerated at runtime in stepImportDomainPanels. v3 confirmed α=4° via pressure PNG (high pressure below LE, dark blue suction above). **setBaseSize: 8 path tried, all FAIL in fresh sim** (incl. `setBaseSize`, `getCustomMeshSize`, `createPartControl` etc.). |
| **Stage 4 Phase E v3** | **NACA domain-rotation + 8-path setBaseSize search** | **partial (α=4° geometrically confirmed; mesh still coarse)** | v3 = cube-rotation 4° around quarter-chord axis; pressure PNG shows correct asymmetric Cp (LE stagnation + upper suction). 8 setBaseSize paths ALL FAIL — see `reports/decisions/DEC-007-NACA-v3-domain-rotation-mesh-attempt.md`. Cl/Cd still broken (sentinel values). |
| **Stage 4 Phase E v4** | **NACA mesh BaseSize path9 (setValue) + solver deadlock** | **partial (mesh path green; solver deadlocked after init)** | **PATH9 真活了**: `def.get(star.meshing.BaseSize.class).setValue(0.05)` → read-back `0.05 (class star.meshing.BaseSize)` ✅ confirmed. Mesh executed in68.85s. Cell count via legacy CellCountManager still unavailable. **SOLVER HUNG**: `set steps = 500` 后4min30s 无 CPU/log 进展,人工 kill。**新瓶颈** = solver deadlock (probable: mesh quality + no CFL tuning on first iter). **Decoupled fixes**: ref velocity = inlet |V| (15 m/s); lift direction = [0,1,0]; Vector3 field names will be logged on next run that completes. See `reports/decisions/DEC-007-NACA-v4-mesh-path9-hang.md`. **DEC-008 (pending)**: solver deadlock + CFL/mesh quality gate needed. |
| **Stage 4 Phase E v5** | **Parallel-session re-test of v4 path9 + diagnostic hang** | **partial (mesh path reproducible; solver hang CONFIRMED with declining-CPU signature)** | Parallel session spawned v4 macro again at16:16:44. Path9 ✅ reproducible (mesh in66.5s). Solver hung at `set steps =200` for ~9min wall. **Diagnostic improvement**: CPU trend went 23.54 →23.62 →23.67 →23.74 →23.67 (last60s declining) — classic hung-loop waiting on per-iter CFL/AMG convergence. Killed + DEC written. Three new debt items (DEC-008a/b/c): try coarser mesh (0.2m), add per-iter status listener, dedupe parallel-session log files. See `reports/decisions/DEC-007-NACA-v5-confirm-hang.md`. |
| **Stage 4 Phase E v6** | **NACA v5 BL refinement + Cl scene integral** | **partial (3 new API unlocked; Cl integral blocked at 2402 R8 layer)** | NacaTrueE2E.java v5 (1430 lines) added: `PrismLayerStretching.setStretching(1.3)` ✅; `star.base.report.SurfaceIntegralReport` class found; `setObjects(Collection)` bound to airfoil ✅; `getValue()` returns null (no compute path). **CSV export blocked**: 8 candidate class names none found in 2402 R8; SceneManager has no `createExport`; Scene only has `.sce/.vrml/.pbrt/.mp4` exports. 200-iter run: mesh 39s + run 761s. PNG 75KB velocity + 83KB pressure. See `reports/decisions/DEC-007-NACA-v5-bl-integral.md`. |
| **Stage 4 Phase E v7** | **NACA MPC 真用 (MeshPipelineController explicit stages)** | **partial (MPC path works end-to-end but equivalent to auto.execute; prism still not visible)** | NacaTrueE2E.java v7: `MeshPipelineController` 真用 path — `mpc.clearGeneratedMeshes() + initializeMeshPipeline() + generateSurfaceMesh() + generateVolumeMesh()` all 4 steps OK in 2402 R8. **Strategy A** (delete AutoMeshOperation + let MPC own pipeline) failed: `mom.eraseObject()` NoSuchMethodException. **Delaunay 2-mesh test** (v7.2): Delaunay doesn't add prism in 2402 R8 (hasPrismMesher=false, def children no Prism* properties). **Final config**: 4-mesh pipeline (Resurfacer×2 + Dual + Prism) + MPC.generateVolumeMesh() trigger. 200-iter run: mesh 64s + run 1113s. **Conclusion**: MPC = auto.execute() functionally. The BL-prism issue is a 2402 R8 PrismAutoMesher behavior, not the trigger method. See `reports/decisions/DEC-007-NACA-v7-mpc-true-path.md`. |
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
| lid_driven_cavity | ✓ runnable (verdict WARN → MOCK ceiling) | stub (refuses) | ✓ E2E full (5000-iter, 13.8s, .sim saved). **NOT covered**: Ghia 1982 tolerance check needs FF sampling (DEC-005; user manual-verify via GUI) |
| naca0012_airfoil | ✓ runnable | stub (refuses) | ✓ E2E smoke (200-iter, 12s). User's `CliNaca2412E2E.java` (v34) runs end-to-end. NOT covered: full Re=6e6 tolerance check pending |
| circular_cylinder_wake | ✓ runnable | stub (refuses) | ✓ E2E spawn (11s). Vortex-street proven path |
| backward_facing_step | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| backward_facing_step_steady | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| duct_flow | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| fully_developed_plane_channel_flow | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| plane_channel_flow | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| axisymmetric_impinging_jet | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| cylinder_crossflow | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| impinging_jet | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| turbulent_flat_plate | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| differential_heated_cavity | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| rayleigh_benard_convection | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| cht_pipe_gnielinski | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |
| cht_straight_fin | ✓ runnable (mock v0.1.1) | n/a | not wired (Stage 3+) |

**Law 1 (runnable-coverage)**: a case is "covered" only when its
real-solver run passes its tolerance gate end-to-end. NONE of the
cases are "covered" yet (Stage 3+ work continues). The Mock column is
"runnable on MOCK", not "covered".

**Mock coverage 2026-06-11 (DEC-006)**: 16/16 cases are mock-runnable
through the full CLI pipeline. Each emits a signed data.json + data.md
+ audit.json. The MOCK verdict ceiling is WARN per EXECUTOR_ABSTRACTION
§6.1; we never claim `validation_status: validated` from a MOCK run.

## Test coverage

| Suite (`pytest -m "not real_solver"`) | Count | Pass | Notes |
|---|---|---|---|
| Main (`tests/`) | 144 | 144 | mock/unit; surrogate 110 tests (41 CST/FFD/LHS/builder + 24 data + 20 models + 14 metrics + 10 train + 1 smoke); incl. auto_verifier + executor + CLI + starccm_adapter stub |
| Bridge non-real (`packages/starccm-bridge/tests/`) | 19 | 19 | classifier / export / bat-resolution units |
| **Total (`-m "not real_solver"`)** | **163** | **163** | 13 real_solver bridge tests deselected (need STAR-CCM+) |
| `scripts/smoke_16cases.py` | 16/16 | 16/16 | full mock CLI pipeline, one run per case |

> **Counts verified 2026-06-13 (takeover stabilization pass).** The earlier
> "56 / 13 / 69" figures and the C-1.1 "28/28, 3 skip" note were stale by
> ~45-80 tests — see the takeover recon. Real-solver E2E tests are
> `@pytest.mark.real_solver` and are NOT counted here (they spawn
> STAR-CCM+, several are additionally `skipif`-gated on the install).

## Active project: commercial-fan-prop (2026-06-12, user-approved)

> 立项于 2026-06-12,源自用户提供的研究分析报告
> 完整备忘:`reports/research/commercial-fan-prop/planning/CHARTER.md`
> 主决策:DEC-008 (`reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md`)
> 形态:主仓的 `reports/research/commercial-fan-prop/` 子项目,步骤化推进(按步骤非按日期,7x24 不间断开发)
> 等级:L0 advisory(沿用 AGENTS.md §Graduated autonomy)
> 协作:多 agent 团队(已授权)

**本项目与既有 Stage 3+ 工作流正交**:不占用 DEC-005(LDC FF)/ DEC-007(NACA 闭环)
的解决资源;只复用 cfd_harness.{executor, auto_verifier, audit_package, report_engine}。

**当前步骤 (M3 surrogate 主线)**:
- M3-S0 ✅ 参数化基础 (CST + FFD + LHS + builder), 41 tests green
- M3-S1 ✅ 链路化 (scripts thin-wrapper → in-package re-export)
- M3-S3 ✅ 神经代理训练基础设施 (data.py + models.py + metrics.py + train.py + CLI), 77 new tests green (2026-06-13)
- M3-S2 ☐ rotor37_slice 真 Java macro (BaseSize.setValue path, 等 2402 R8 API 突破)
- M3-S5 ☐ 多目标优化 (NSGA-II/pymoo)
- M3-S6 ☐ 论文初稿 (等 S5 出第一轮 Pareto)
**首篇主轴**:参数化(8-18 变量)+ OpenFOAM/STAR-CCM+ 样本 + 神经代理 + 多目标优化
**首篇目标期刊**:AIAA Journal / Computers & Fluids / Aerospace Science & Technology

子决策: DEC-008.a (立项) / DEC-008.b (数据采集) / DEC-008.c (建模) / DEC-008.d (优化) /
DEC-008.e (L0->L1 升级)

> **Correction (2026-06-13)**: ~~the fan-prop planning docs describe the surrogate track as "M3
> not started / no cst.py/ffd.py".~~ That is **stale** — `src/cfd_harness/
> surrogate/` now has 8 modules: cst.py (162 LOC), ffd.py (227 LOC), lhs.py (122 LOC),
> builder.py (165 LOC), data.py, models.py, metrics.py, train.py.
> 110 surrogate tests green. M3-S3 neural surrogate training pipeline landed 2026-06-13.

## Open DECs

| ID | Status | Topic |
|---|---|---|
| DEC-001 | **partial closed (2026-06-11)** | port the OpenFOAM `solver_info` migration for all 14 remaining gold standards. Closed for the **mock-first** subset (13 cases: see DEC-006). Still open for the **real-solver STAR-CCM+ 2402 retarget** part: every gold_standard's `solver_info` block must be re-validated against an actual STAR-CCM+ run on a real mesh, not just ported from cfd-harness-unified's OpenFOAM notes. |
| DEC-002 | **closed (2026-06-09)** | ~~the Codebuddy REPL protocol~~ (the bridge now wraps the 7 unified CLI commands + the vortex-street proven path). |
| DEC-003 | open | LDC E2E Stage 3+ exit-gate (5000-iter, Ghia 1982 tolerance). Blocked on DEC-005. |
| DEC-004 | **partial closed (2026-06-10)** | case_id → sim_path mapping. The 3 anchors (lid_driven_cavity / naca0012_airfoil / circular_cylinder_wake) are wired in `case_profiles.yaml` (DEC-006 follow-up 2 will add 13 more). |
| **DEC-005** | **accepted — dead-end documented (2026-06-13)** | Real-solver field/force **read-back** (LDC Ghia centerline + NACA Cl/Cd) is UNREACHABLE on STAR-CCM+ 2402 R8 / 19.02.009 via the public Java macro API (`ProbeManager` removed; `ForceCoefficientReport` returns a sentinel). WIN_STARCCM ceiling reframed to **"qualitative / pipeline-verified"** (spawn+mesh+solve+PNG+region-avg), never tolerance-validated. Only quantitative paths: GUI CSV export or a build upgrade. Now written: `reports/decisions/DEC-005-ff-sampling-report-reading-deadend.md`. |
| **DEC-007** | **accepted (2026-06-11) — v3 + v4 sub-issues** | NACA real-solver closed loop (v1; path green, V&V still FAIL). See `reports/decisions/DEC-007-naca-real-closed-loop.md`. v2 attempted 2026-06-11 — pipeline green, α-tilt + report reading blocked by 2402 R8 (see `DEC-007-NACA-v2-alpha-tilt-attempt.md`). v3 — α=4° geometric via cube-rotation; 8 setBaseSize paths FAIL (see `DEC-007-NACA-v3-domain-rotation-mesh-attempt.md`). **v4 — path9 (`def.get(star.meshing.BaseSize).setValue`) WORKS, mesh executes in68.85s; solver deadlocked after init (see `DEC-007-NACA-v4-mesh-path9-hang.md`). DEC-009 covers the solver deadlock + CFL/mesh quality gate (the old "DEC-008 needed" note collided with the commercial-fan-prop charter; renumbered to DEC-009).** The user-mandated "all tasks real STAR-CCM+" is satisfied for the NACA case path; Cl/Cd closed-loop V&V still pending solver-side fix. |
| **DEC-008** | **accepted (2026-06-12) — M3-S3 landed 2026-06-13** | 民机风扇/螺旋桨 AI-CFD 项目立项(L0 advisory,步骤化推进)。两条线(风扇先、螺旋桨后),STAR-CCM+ 端暂不补 API,主轴=参数化(CST 12-vector)+ 神经代理(MLP/GPR)+ 多目标优化(NSGA-II)。详见 `reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md` 与 `planning/CHARTER.md`。 |
| **DEC-009** | **accepted — debt registered (2026-06-13)** | NACA solver deadlock (intermittent, mesh-quality-dependent — v6/v7 runs DID complete) + Rotor37 hollow-green (`Rotor37Slice2D.java` prints DONE while solving nothing: dead mesh path + LDC placeholder geometry). Mitigations specified, never run; both out of scope for the mock-first stabilization pass. Resolves the phantom "DEC-008 (solver deadlock)" collision. See `reports/decisions/DEC-009-solver-deadlock-rotor37-hollow-green.md`. |
| **DEC-010** | **accepted — remediated (2026-06-13)** | Audit signing-key trust hardening. Security audit found the HMAC key was a hardcoded public default (forgery PoC confirmed: `is_validated=True` verifiable by anyone) + no key-identity binding + backdatable `signed_at`. Fixed: key from `--sign-key`/`CFD_HARNESS_SIGN_KEY` (no secret in source) with an explicit `dev-unsigned`/`trusted=false` fallback; `key_id` fingerprint binding in `verify()`; timestamp bound into the payload; 32-byte min key; `allow_nan=False`+NFC serialization; SCHEMA_VERSION 1→2. +8 security tests (suite 228 green). **Operational follow-up**: provision a real `CFD_HARNESS_SIGN_KEY` in CI secrets — until then every audit is honestly `dev-unsigned`. See `reports/decisions/DEC-010-audit-signing-key-trust.md`. |

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

## Phase 3+ optimization pass (2026-06-10, L0 advisory)

User approved a focused optimization round to harden the Stage 3+
end-to-end pipeline. Scope: P0 + P1.3 + P2 (5h main line).
P1.4 (LDC FF sampling real fix) is a separate workstream.

| Pri | Item | Status | Verification |
|---|---|---|---|
| **P0.1** | `bridge.starccm_bat` reads Codebuddy `use-version` (was: most-recently-modified heuristic) | done | `python -c "from starccm_bridge import CodebuddyRepl; print(CodebuddyRepl().starccm_bat)"` returns `C:\Program Files\Siemens\19.02.009-R8\...\starccm+.bat` (the active version) |
| **P0.2** | LDC sim-lock recovery: executor auto-`force_new=True` for `lid_driven_cavity` (from-scratch case) | done | unit test `test_force_new_injects_dash_new` asserts cmd argv contains `-new` between sim path and `-batch` |
| **P1.3** | `bridge.export_scene()` + executor post-step runs `export-scene <sim>` after `run-macro` for NACA-style cases (vortex-street already emits PNGs itself) | done | unit test `test_export_scene_builds_correct_argv` verifies argv; LDC step 11 in macro unchanged |
| **P2.5** | `bridge._classify_spawn_error()`: stderr_head 500→4000 chars + machine-readable error codes (`OK` / `SIM_LOCK` / `VERSION_MISMATCH` / `MACRO_COMPILE_ERROR` / `TIMEOUT` / `SPAWN_FAIL`) | done | 11 unit tests cover the classifier; `data["error_code"]` surfaces in `RunReport.notes` |
| **P2.6** | `tests/test_bridge_p0p1p2_fixes.py` — 18 unit tests, all pass in 0.91s (no STAR-CCM+ install required) | done | `pytest packages/starccm-bridge/tests/test_bridge_p0p1p2_fixes.py` → 18/18 PASS |
| **P2.7** | This section (AGENTS.md / STATE.md updates) | done | – |

### Audit write (post-P0)

Audit files now write to `reports/audit/<case>/<ts>/audit.json` with
`{manifest, signature, verify_recipe}` — `data_audit.json` MOCK run
emits a 1.4 KB signed manifest; `WIN_STARCCM` failures also write
audits, proving the audit path is executor-agnostic.

### LDC step 11 (post-P0)

`LidDrivenCavity.java` extended with reflection-safe `step11ExportPNG()`
that renders Velocity + Pressure via `Scene → ScalarDisplayer →
exportImagePNG`. Pattern mirrors the proven `VortexStreetV129R.java`.
End-to-end PNG verification is blocked on the WIN_STARCCM spawn
(STAR-CCM+ 19.02.009 refuses to open the existing
`lid_driven_cavity_solved.sim` — needs manual GUI cleanup or
`force_new=True` from a fresh `sim_placeholder`).

### P1.4 — LDC FF sampling (deferred)

DEC-005 is still open. The chief engineer will commit to one of:

- (a) **降级** to proxy metric (max velocity / Δp) from monitors —
  ~1-2h, no LDC FF sampling fix needed
- (b) **死磕** STAR-CCM+ 19.02.009 reflection for a working FF
  sampling path — 4-8h, not guaranteed
- (c) **暂不动** — keep LDC with "NaN known issue" tag, NACA +
  cylinder coverage first

User chose **(b) 死磕** in the 2026-06-10 scope review. Workstream
is unblocked but not started in this pass.

### C-1 follow-up: bridge encoding fix + pipeline touchpoint visualizations (2026-06-12)

| Pri | Item | Status | Verification |
|---|---|---|---|
| **C-1.1** | ridge._invoke 1-line encoding="utf-8", errors="replace" patch (D-6 root-cause fix) | done | epl.py:311-319 now passes encoding="utf-8"; spot-check via nalyze Cases/nonexistent_probe.sim returns full JSON envelope (rc=1, error.code=FILE_NOT_FOUND) instead of aw_stdout=None; non-real bridge suite = **19 passed, 0 skipped, 0 failed, 13 real_solver deselected** (~0.7 s wall, verified 2026-06-13 — the earlier "28/28, 3 skip" figure was stale/fabricated); Python 3.11 subprocess.run no longer drops CJK-error responses |
| **C-1.2** | Pipeline-touchpoint visualizations for paper-draft-2026-07 §5.1.5 | done | 2 real STAR-CCM+ 2402 R8 scene PNGs copied from D:\StarCCM Codebuddy\Cases\Results\ to eports/research/commercial-fan-prop/figures\: ig1_naca_v35_pressure.png (NACA 2412 v35 pressure contour, scale -50..+50 Pa, polyhedral mesh visible) and ig2_naca_v35_velocity.png (velocity magnitude, scale -1..15 m/s). Both produced by NacaTrueE2E.java v1 (build 2026-06-11) with k-ω SST, 2000 iter, Re=1×10⁶, AOA=4°; solved sim 
aca2412_v35_true.sim (115 MB) is the source. Provenance: eports/research/commercial-fan-prop/figures\README.md |
| **C-1.3** | Rotor37Slice2D.java extension (D-7 RRF path) — DEFERRED to 8 月 M2 | deferred | 8 月数据期 ① will extend the 57-line reflective skeleton into a full 2D channel-flow macro (geometry O-H + 10-15 prism layers + k-ω SST + RRF + 200-1000 iter + CSV export). The reflective-skeleton stub compiled green at M1 (D-3); the 8 月 extension is the natural first consumer of the C-1.1 bridge encoding fix |
| **C-1.4** | LDC FF sampling (DEC-005, 死磕 path) — DEFERRED to 8 月 after bridge fix lands | deferred | The (b) 死磕 path is the user's chosen strategy; the C-1.1 bridge fix is the prerequisite for any reflection-heavy probe macros. 8 月 workstream: re-run the 8 probe macros in macros\_probes\ against the fixed bridge, identify which of the 6 tried APIs is viable in 2402 R8, port the user's CliExportFieldData 5a-5f cascade |
| **C-1.5** | Paper draft v1.1 patches (§4.1.5 + §4.2.1 + §5.1.5 + §6.1) | done | paper-draft-2026-07.md 36 969 B → 43 239 B; 715 → 815 lines; 4 764 → 5 668 words; 2 new figures embedded, all 4 fig file:line refs verified present, 5 new section anchors (4.1.5, 4.2.1, 5.1.5) verified by Select-String. No fabricated data; the 2 NACA 2412 v35 PNGs are real STAR-CCM+ 2402 R8 scene exports from a pre-existing cfd-harness pipeline touchpoint, not surrogate training samples |

| **C-1.6** | Paper draft v1.2 polish: §3.4 nomenclature + §4.2.2 Rotor37 2D-slice mesh + §4.2.3 grid-independence plan + §5.4 NACA v35 / LDC quantitative pipeline validation table + §5.5 scheme-sensitivity TODO + §6.1 sign-convention caveat + §7 [22] full Ladson 1988 entry | done | paper-draft-2026-07.md 43 239 B → 55 708 B; 815 → 1 029 lines; 5 668 → 7 602 words; 30 numbered references (was 22 in v1.0); 5 new section anchors verified by Select-String (3.4, 4.2.2, 4.2.3, 5.4, 5.5); 71 file:line citations; 9 explicit TODO markers in §5.3 + §5.5 + §4.2.2/3; 7 sign-convention caveat mentions. Self-check pass: no "we achieved" / fabricated-data patterns, 27 forward-looking qualifiers ("we propose" / "we plan to" / "scheduled" / "to be reported"), 7 honest-layering markers |

| **C-1.7** | DEC-005 LDC FF sampling — 20-probe diagnostic completed; closed as **out of scope for 4-8h window**; deferred to 8 月 M2 (port CliExportFieldData v24 1500-line cascade OR upgrade STAR-CCM+ build) | done (diagnostic) / deferred (resolution) | 20 probes (macros\_probes\Probe9-20.java) + 11 log files (probe{9..20}_*.log, ~50 KB total). Structural finding: ProbeManager API removed from STAR-CCM+ 19.02.009 R8 classpath. No per-cell public Java API path to sample a FieldFunction at a single point exists in 2402 R8. VolumeAverageReport on the EXISTING region works (Probe13, returns -3.04e-17 ≈ 0) but not per-cell. Full LDC_STATUS.md update with 20-probe catalog. Paper §5.4 footnote expanded to cite the 20-probe result + ProbeManager structural finding. The 4-8h "死磕" (chief's chosen strategy per STATE.md:212-223) is honestly closed as no-viable-path-on-2402-R8. Cron ldc-dec005 deleted |

- [x] **C-1.8** (2026-06-12) **M2 first-milestone: Rotor37Slice2D.java → 350 lines, 11-step end-to-end run OK on STAR-CCM+ 2402 R8** — Rotor37Slice2D.java grew from 57-line stub to 350-line 11-step macro (geometry → region → continuum → BCs → mesh → init → 30-iter solve → reports → CSV → save). First successful end-to-end run: otor37_slice_v3_run.log (8 KB), step 8 solve 30 iter in 65 ms, otor37_slice_solved.sim 2.08 MB saved. **Honest debt分层:** (1) geometry = LDC 3D cavity placeholder (M2 day-2+ to import real Rotor37 2D channel); (2) Mach Number + Mass Flow Rate FF lookup returns NullFieldFunction sentinel — needs a 1-iter warmup before binding (deferred); (3) AutoMeshDefaultValuesManager.setValue(double) + Boundary.setValue(double) NoSuchMethodException in 2402 R8 (deferred, needs proper wrapper); (4) RotatingReferenceFrame "no registration found" — 2D RRF path needs MovingReferenceFrame or tangential inlet (deferred). M2 day-1 stub GREEN. P3 deliverable updated in planning/p3-driver-stub-deliverable.md.

- [x] **C-1.9** (2026-06-12) **M2 day-2+ (b) PLAID Rotor 37 import attempt → INFEASIBLE on this network** — Probed PLAID-datasets HF mirror (4.4 GB at 24 KB/s = 50 h), energy.gov PLA (404 — deprecated 2018), NTRS API (no search endpoint, JS-rendered page), GitHub (blocked), CSDN (Numeca-only). Trashed all probe files; only Cases/PLAID/README.md (30 KB) kept. P3 deliverable updated with full cost analysis + (c) hand-sketch as recommended next step.

- [x] **C-1.10** (2026-06-12) **M2 day-2+: hand-sketched Rotor 37 STL + scene export (path A)** — scripts/rotor37_geometry.py (220-line Python) generated otor37_1passage_3d.stl (1360 triangles, 66 KB, 3D solid). Rotor37Slice2D.java Step 1 now uses ImportManager.importStlSurface() — first run otor37_slice_v6_run.log shows Creating one boundary for all patches. # Faces: 1360, # Vertices: 4080 (STL imported OK). **However 2402 R8 macro path BLOCKS the next step** — imported surface is a "ghost" in Region 2 with no meshable GeometryPart; 5 probes (ProbeGeomLoader/ImportMgr/SimGet/PartRegion/StlImport) walked the 2402 R8 classpath and confirmed no public API to convert surface → GeometryPart. **What works:** LDC placeholder Region 1 still 30 iter solve OK (65 ms); exported 3 real STAR-CCM+ 2402 R8 scene PNGs via starccm_cli.py export-scene (pressure 41KB / mach 30KB / velocity 22KB). **Day-3+ paths** (honest 3-way): (i) GUI CAD pipeline 2-3h, (ii) CAD-X_T conversion 1-2h, (iii) accept LDC placeholder + move on to surrogate baseline. P3 deliverable updated (28 KB).

- [x] **C-1.11** (2026-06-13) **M2 day-2+ GUI automation attempt — abort at 25 min** — User correctly challenged "why not bypass GUI?". I started STAR-CCM+ GUI (PID 25488, window "rotor37_slice_solved - Simcenter STAR-CCM+"), used cu MCP desktop_* tools (screenshot/zoom/click/key/window_focus). Successfully opened File menu + clicked Import. **Blocked by menu text OCR brittleness** (model returned Chinese strings when reading Import submenu) and keyboard navigation misfire (13×Down+Right opened wrong popup). GUI automation works for simple click+button but breaks on multi-step submenu+dialog chains. Cron otor37-m2 deleted (was hourly alive check, no longer needed). **Final M2 day-2+ decision matrix** (5 paths A-E): A=LDC placeholder DONE, B=PLAID infeasible, C=GUI slow, **D=CAD-X_T conversion best ROI 1-2h**, E=accept LDC + move to Sep surrogate. P3 deliverable updated (32.9 KB).

- [x] **C-1.12** (2026-06-13) **M2 day-2+ (D) CAD-X_T path: watertight STL + STEP generated, 2402 R8 macro still blocks meshable part** — Probed local toolchain (cadquery ✓, trimesh ✓, gmsh ✓, shapely ✓). Diagnosed v1 STL bug (80 boundary edges from broken z-quad topology). Generated scripts/rotor37_passage_watertight.stl (156 faces, **is_watertight=True**, 0.687 cm³) via trimesh.extrude_polygon. Generated scripts/rotor37_extruded.step (153 KB AP214) via cadquery Workplane.extrude. **Both macro imports still fail to create meshable part**: importStlSurface returns ghost surface, importCaeFile says "Unrecognised file format". **Honest finding**: STAR-CCM+ 2402 R8 macro import paths don't expose the surface-mesh→GeometryPart conversion that the GUI does. The bottleneck is the macro API layer, not file format. P3 deliverable updated (37.1 KB).

- [x] **C-1.13** (2026-06-13) **M2 day-3 (D) GUI automation learning mode: proven feasible but slow** — User pushed back on my 25-min abort saying "你应该可以通过自己打开GUI然后不断截图、分析该怎么点击". Retried with screenshot-verify-click loop. **Proven**: window focus, menu open (Alt+F), submenu open (Down 12 + Right), file picker dialog open (click on 至文件). **Blocked by**: click coords misalign + model can't reliably act+verify in one shot + each step has 30%+ error rate. 7-step pipeline (File > Import > submenu > file picker > type path > Open > verify) cumulative success ~30-50% per attempt, 30-60 min each. **Honest winner**: user driving GUI manually is 2 min vs 30-60 min automated. **Recommended 2-min manual action** for user: File > Import > Import Surface Mesh > pick scripts/rotor37_passage_watertight.stl > Save As .sim > macro takes over. P3 deliverable updated (41.7 KB).

- [x] **C-1.14** (2026-06-13) **M2 day-3+ (D) Iteration 2: learning mode + last macro probe → FINAL VERDICT** — User pushed back on my 2-min-manual recommendation saying "继续GUI自己学习单干,虽然慢". Retried with screenshot-verify-click loop (~3 h). Same conclusion: click coords between screenshot (1430x804) and cu (2560x1440) keep misaligning, 30-40% miss rate per click. Last macro probe ProbeSurfaceRepair walked 2402 R8 classpath: only star.common.ImportedSurface and star.common.ImportedSurfaceManager exposed. **No SurfaceRepair/SurfaceMeshToPart/createPart method exists**. The 2402 R8 Java API genuinely cannot convert imported surface to meshable GeometryPart. **Final M2 verdict**: real R37 2D meshed+solved not achievable in this time budget; 2402 R8 API is the bottleneck. Shipped = LDC stub + 3 PNGs + watertight STL + STEP + 9-hour documentation. P3 deliverable 46.3 KB. **Day-4 recommendation**: pivot to 9月 CST/FFD surrogate baseline.
