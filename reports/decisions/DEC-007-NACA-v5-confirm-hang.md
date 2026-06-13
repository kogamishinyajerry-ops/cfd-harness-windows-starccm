# NACA v5 — parallel-session test of v4 path; solver hung after init

| Field | Value |
|---|---|
| Status | **partial** — solver hung post-init; no Cl/Cd captured |
| Date | 2026-06-11 |
| Branch of | DEC-007 v4 |

## TL;DR

A parallel session (or autonomous run triggered after the v4 DEC) re-ran the v4 macro with the **path9 mesh fix** at16:16:44. **Mesh path verified working** (BaseSize.setValue(0.05) → read-back OK, mesh executed in66.5s). **Solver initialized, then hung** at `set steps =200`. Killed at16:25 after ~9 min wall with no CPU/log progress and a declining CPU trend (23.74 →23.67 in last60s = classic hang fingerprint).

**Net: v4's path9 mesh fix is confirmed working in a fresh, parallel-spawn context.** The solver-deadlock hypothesis from v4 still holds: even with path9 working, the k-omega SST solver on this mesh quality + initialization deadlocks after `set steps`.

## What this v5 attempt added (vs v4)

**Strictly a re-test of v4's path9 path** — same macro (`NacaTrueE2E.java`), same NACA_ITERS override pattern, same mesh setup. No code changes. The parallel session triggered it independently after I sent the v4 DEC at15:59.

| Stage | v4 (15:49 spawn, killed at15:54) | v5 (16:16 spawn, killed at16:25) |
|---|---|---|
| Mesh path | path9 ✅, read-back0.05 ✅ | path9 ✅, read-back0.05 ✅ |
| Mesh execute | 68.85s | **66.5s** (similar — confirms path9 reproducible) |
| Init | OK | OK |
| Iters requested | 500 | **200** (parallel session chose shorter) |
| Iters completed | unknown (killed before stdout flushed) | unknown (no stdout captured this spawn) |
| Wall to kill | ~4.5 min | **9 min** (gave it more time) |
| CPU trend at kill | flat 23.2s | **declining** 23.74→23.67 (-0.07 in60s) |
| .sim saved | 0 bytes | 0 bytes |

The **declining CPU** is the new signal: in v4 I killed at flat-CPU. In v5, CPU actually started going DOWN, which is more diagnostic of a hung loop waiting on a condition that never satisfies (likely a sync barrier or a per-iter CFL/AMG convergence check that times out internally).

## Diagnosis: solver deadlock on this mesh

The combination of:
- k-omega SST (3 nonlinear iterations per outer step)
- 0.05m base mesh size (likely ~150k cells in a 6m cube with prism layers)
- α=4° via cube rotation (asymmetric inflow)
- Cold-start initialization (no field from prior sim)

…almost certainly produces an initial transient where the AMG linear solver fails to converge per inner iter, and the outer step's CFL relaxation kicks in. STAR-CCM+ has an **inner-iteration limit per outer step** (typically 5-10) — when all inners fail to converge, the outer step records "iteration diverged" and either backs off CFL or gives up. In our case, the macro calls `simIter.run()` which blocks until all 200 steps complete OR a stop condition triggers. The latter isn't happening → infinite loop on per-iter divergence.

**Two candidate root causes:**
1. **Mesh quality on airfoil surface**: the prism layer may have invalid cells near the LE stagnation point + trailing edge, causing first-iter linear-solver divergence
2. **Pressure outlet initialization**: setting pressure outlet to atmospheric from a uniform initial field with α=4° inflow may produce a strong startup shock that AMG can't handle

## Decision points (new debt)

This v5 attempt **confirms** v4's hypothesis (path9 mesh works, solver is the next bottleneck). Three new debt items:

### DEC-008a — solver divergence on coarse NACA mesh
- **Severity**: HIGH — blocks the entire NACA closed-loop path
- **Owner**: chief-engineer
- **Mitigation**: try mesh size **0.1m or0.2m** (much coarser) first to see if the solver runs at all. If yes, refine down. If no, problem is initialization not mesh.
- **Estimated**: 1-2h to test + adjust

### DEC-008b — no per-iter progress logging in macro
- **Severity**: MEDIUM — makes hang detection impossible without external monitoring
- **Owner**: starccm-adapter-engineer
- **Fix**: add a per-iter writeLog inside `simIter.run()` callback, OR set `simIter.getClass().getMethod("setExecutionStatusListener", ...)` if it exists
- **Estimated**: 30min code change + 1 test run

### DEC-008c — parallel-session spawns conflict on same .sim
- **Severity**: LOW — caused the duplicate log file we saw today
- **Owner**: chief-engineer (policy)
- **Mitigation**: add a session-id-prefixed log filename pattern; refuse to spawn if NACA_ITERS env mismatch between runs
- **Estimated**: 10 min policy doc + 1 runner script change

## X% done / Y% not (cumulative NACA across v1-v5)

### ✅ Done (cumulative)

| Item | When |
|---|---|
| StarCCM+ bridge (`CodebuddyRepl` subprocess) | v0 |
| Mesh path: `def.get(star.meshing.BaseSize).setValue` confirmed | v4 |
| Domain rotation α=4° via cube geometry | v3 |
| Physics: k-omega SST + segregated flow + ideal gas + energy | v2 |
| BCs: Inlet xmin / Outlet xmax / Sym ybot ytop zin zout / Wall airfoil | v2 |
| Reference area =0.05 m² (chord × span) | v4 |
| Reference velocity = inlet |V| (15 m/s) | v4 |
| Lift direction = [0,1,0] | v4 |
| PNG export: velocity + pressure | v3 |
| Vector3 field-name logging (when getValue returns Vector3) | v4 |

### ❌ Not done (cumulative)

| Item | Severity |
|---|---|
| 500-iter steady solver run completes | **HIGH** (5 attempts, all hung) |
| Real Cl/Cd/Cm extracted from report | **HIGH** (no run finished) |
| V&V vs Ladson 1988 gold tolerance | **HIGH** (blocked on Cl/Cd) |
| α-tilt via vector profile (currently geometry-only) | MEDIUM |
| Mesh BaseSize0.005m (currently 0.05m smoke grade) | LOW |
| Cell count (legacy CellCountManager 不可用) | LOW |
| Mesh quality report + first-iter divergence log | MEDIUM |

## 给下一会话

The honest state is: **the v4 NACA path goes 9 steps out of 11** (import → domain → subtract → region → physics → BCs → inlet → mesh → init → solver). The first 9 are green. Step 10 (init) succeeds. Step 11 (200+ iter) reliably hangs.

To break through, you have three options ordered by ROI:

1. **Try a coarser mesh (0.1m or 0.2m)**: cheapest, fastest test. If solver runs at 0.2m, problem is mesh quality. ~30min.
2. **Add a per-iter status listener to the macro**: gives diagnostic info without changing physics. ~30min.
3. **Switch from k-omega SST to Laminar or k-epsilon**: simpler turbulence model may converge where SST chokes. ~1h including macro edit.

If you want me to pick — I'd do (1) first since it's the cheapest signal.

## 给你看

- `D:\StarCCM Codebuddy\Cases\Results\naca_true_v1.log` (10746 bytes — last write16:18:00, frozen since)
- `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true_smoke.sim` (0 bytes — reserved by STAR-CCM+, never written)
- (no stdout this spawn — different runner than the parallel session's `run_naca_macro.py`)
- 0 active `starccm+` processes (cleaned)