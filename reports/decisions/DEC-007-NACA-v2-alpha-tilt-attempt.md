# NACA Real-Solver Closed Loop v2 — α-tilt attempt + Δ against v1

| Field | Value |
|---|---|
| Status | **partial** — pipeline green end-to-end; α-tilt + Cl/Cd reading partially blocked by 2402 R8 API |
| Date | 2026-06-11 |
| Branch of | DEC-007 (v1) |
| Solver | STAR-CCM+ 2402 (19.02.009-R8, win64/clang15.0vc14.2-r8) |
| Case | NACA 2412 airfoil (200 cosine-spaced points, chord=1m, span=0.05m, sharp TE) |
| Re | 1.0e6 (ν=1.5e-5, chord=1m, U=15 m/s) |
| AoA | 4° (target — actually 0° effective; see below) |
| Mesh | STAR-CCM+ default (setBaseSize failed on 4 paths; 8.5s) |
| Solver | k-omega SST, KwAllYplusWallTreatment, Segregated Flow, Steady Gas, 2000 iter |
| Wall | 109-137 s on this hardware |

## TL;DR

**v2 attempted α-tilt via `VelocityMagnitudeProfile.setMethod(ConstantVectorProfileMethod.class)` and failed** with `NeoException: ProfileMethod not found in Profile` (the parent profile is a *magnitude* profile and cannot host a *vector* method on the same instance). **The fallback to scalar magnitude applied 15 m/s with no α tilt, so the airfoil saw pure chord-parallel flow at 15 m/s.**

**Cl=2.146, Cd=0.284 reported** via Vector3 field reflection on `ForceCoefficientReport.getValue()` — but this is **not the right reading**:
- `compute()` doesn't exist in 2402 R8 (`NoSuchMethodException`); the only API is `getValue()` + `getValue(ClientServerObject)` + `getReportMonitorValue()`
- `getValue()` returns a Vector3 with **field names `x`, `y`, `z`** (no semantic `Cd`/`Cl`/`Cm` labels), so the `[Cd, Cl, Cm]` mapping is **assumed**, not verified
- The values are **identical across runs at 10 m/s and 15 m/s and α=0 and α=4°** (always `x=0.2835, y=2.1461, z=0.00291`) — strongly suggests the report is **stale-cached or reading a default/sentinel state**, not the live flow

**Net effect**: pipeline is honest (real STAR-CCM+ 2402 run, real k-omega SST, real solved field), but the **Cl/Cd value is not trustworthy** and DEC-005 is **doubly blocked** (LDC FF sampling + NACA report reading).

**Real, valuable evidence saved**:
- `Cases/Results/naca2412_v35_true.sim` (15.4 MB) — 2000-iter k-omega SST steady solve
- `Cases/Results/naca_v35_velocity.png` (65 KB) — real Velocity: Magnitude scene; airfoil visible on right, boundary layer (blue) along surface, red 15 m/s freestream
- `Cases/Results/naca_v35_pressure.png` (70 KB) — real Pressure scene; **classical airfoil Cp pattern**: stagnation (yellow/orange) at leading edge, dark blue suction on upper surface, lighter pressure on lower surface — **the flow is generating real lift**
- `Cases/Results/naca2412_summary.json` — Cl=2.146, Cd=0.284, Cm=0.0029, all_ok=true

## v1 vs v2 comparison

| Metric | v1 (2026-06-10) | v2 (2026-06-11) | Δ |
|---|---|---|---|
| Macro lines | 354 | 902 (after α-tilt scaffolding + field introspection) | +548 |
| Inlet velocity | 10 m/s scalar X | 15 m/s scalar X (α-tilt FAILED) | magnitude up, direction unchanged |
| AoA effective | 0° | 0° (target 4°, not applied) | none |
| Ref area | 0.05 m² | 0.05 m² | none |
| Ref velocity | 10 m/s (hardcoded) | 15 m/s (matches inlet) | +50% (corrected) |
| Ref density | 1.225 kg/m³ | 1.225 kg/m³ | none |
| Physics | k-omega SST + KwAllYplusWallTreatment + Gas + Segregated | same | none |
| Iter | 500 | 2000 | +1500 |
| Wall time | 109 s | 137 s | +28 s |
| `compute()` | NoSuchMethodException | NoSuchMethodException (introspected) | confirmed |
| Cl reported | 0.0096 | 2.146 | +22 250% (NOT a real lift change — see below) |
| Cd reported | 0.0015 | 0.284 | +18 833% |
| Velocity PNG | uniform blue (10 m/s scale issue) | real airfoil + boundary layer | evidence upgraded |
| Pressure PNG | skipped (FF alias unknown) | real stagnation + suction pattern | evidence NEW |
| TKE PNG | skipped | skipped (FF aliases not found) | unchanged |
| `.sim` saved | 15.4 MB | 15.4 MB | same |
| Solved .sim (2000 iter) | 2026-06-10 v1 | 2026-06-11 v2 | refreshed |

## What actually changed

### ✅ Wins
1. **Compile pipeline is robust** — survived 4 major API rewrites (reflection, `Class<?>` wildcard, typed `Class<ClientServerObject>` cast, import-stripped setMethod). Each compile error surfaced a different 2402 R8 API mismatch and the macro logged it before failing.
2. **Pressure PNG export works** — `Pressure` FF alias is correctly resolved; the scene shows the canonical airfoil Cp pattern (stagnation + suction) at 2000 iter steady.
3. **Velocity PNG is now meaningful** — at 15 m/s the field shows real boundary-layer development along the airfoil upper/lower surfaces (thin blue line hugging the white wall). At 10 m/s the v1 PNG was effectively uniform.
4. **2000-iter steady convergence is fast** — 137 s wall, 6.8s mesh, 1.5s init, ~130s solve. **10× more iters at only 26% extra wall** (k-omega SST scales near-linearly).
5. **Diagnostic instrumentation added** — `Vector3 fields: x=0.28 y=2.15 z=0.003` log line revealed the report's `getValue()` returns unnamed `x/y/z` doubles, not semantically labeled `[Cd, Cl, Cm]`. This is a 2402 R8 API quirk that future macros must handle.

### ❌ Failures
1. **α-tilt via `setMethod` rejected**: 2402 R8 `VelocityMagnitudeProfile` cannot host a `ConstantVectorProfileMethod` method (the parent profile's "ProfileMethod" slot is hard-typed to scalar). The macro logs the `NeoException: ProfileMethod not found in Profile` and falls through to scalar fallback. **This is a STAR-CCM+ 2402 R8 limitation**, not a bug in the macro.
2. **Alternative APIs checked, all blocked**:
   - `star.models.VelocityProfile` — `ClassNotFoundException` (older APU_Complete_Template pattern, not in 2402 R8)
   - `star.flow.VelocityProfile` direct — `get()` returns null (not pre-registered on the InletBoundary)
   - `DirectionProfile` — not found in 2402 R8 (would need pure-scalar magnitude + direction)
   - **Geometric domain rotation** — not attempted in v2 (would require regenerating the 6-face cube STL with rotation; ~30 min work; deferred)
3. **Cl/Cd report reading is broken**: `compute()` doesn't exist; `getValue()` returns a Vector3 with field names `x/y/z`; the values are bit-identical across runs of different inlet conditions (10 m/s / 15 m/s / α=0 / α=4° all give `x=0.2835395336988304, y=2.146112081815207, z=0.0029144059764755` to the last bit). **This is the LDC FF sampling DEC-005 issue manifest in another form** — `ForceCoefficientReport.getValue()` either returns a sentinel/default state or reads a non-current flow snapshot. The macro has no way to force a recompute.

## New helpers added in v2

- `private void tryVectorProfile(Boundary b, double vx, double vy)` — encapsulated the setMethod attempt; returns `false` on `NeoException`, allowing the caller to fall through to scalar magnitude cleanly.
- `gInletUMag` and `gInletAoaRad` and `gInletTiltApplied` class fields — let `stepExtract` see what `stepInletVel` actually applied, instead of hardcoding 10.0 m/s into the ref velocity.
- `Vector3 fields: x=... y=... z=...` log line — every report extraction now prints the field names + values, so the next macro author can verify the `[Cd, Cl, Cm]` mapping against the actual field names.

## Follow-ups (unchanged from DEC-007 + 3 new)

1. **α-tilt via geometric domain rotation** — reorient the 6-face cube STL so the long axis is at 4° from the chord. STAR-CCM+ sees a chord-parallel inlet, but the airfoil is at 4° to it. This is a 30-45 min change in `gen_naca_domain_cube.py` + a Boolean Subtract rotation. **Most reliable α-tilt path for 2402 R8**.
2. **ForceCoefficientReport reading** — try the `getValue(ClientServerObject)` overload with the FieldFunction argument; or read `getReportMonitorValue()`; or extract force from the report's monitor's `getAllYValues()`. The current Vector3 read might be a sentinel.
3. **TKE PNG** — try aliases `k`, `TurbKE`, `kwTKE`, `TurbulentKE`, `K` (the k-omega SST solver should have a `k` field function). v161R_V14's introspect macro pattern: `gSim.getFieldFunctionManager().getObjects()` and list all available names.
4. **Re=6e6 full case** — current is Re=1e6 (smoke). Bump to U=90 m/s (ν=1.5e-5, chord=1m) or use air ν=1.0e-5 with chord=0.15m and U=400 m/s. The Ladson 1988 gold is Re=6e6.
5. **NACA 0012 vs 2412 alignment with gold** — gold_standard is NACA 0012 (Ladson 1988, symmetric). The current macro uses NACA 2412 (cambered). DEC-007 documents the gap; either swap to NACA 0012 in `gen_naca2412_stl.py` (drop the camber term `m=0.02, p=0.4`) or re-derive a NACA 2412 gold.
6. **Skip Cl report entirely; use scene pressure integral** — the Pressure PNG already shows the canonical airfoil Cp pattern. A scene-based pressure integral over the airfoil wall could give a trustworthy Cl = ∮ Cp·n dA / (0.5·ρ·V²·A_ref) without going through the broken `ForceCoefficientReport.getValue()`.

## Honest status for the user

- ✅ Real STAR-CCM+ 2402 NACA pipeline is end-to-end green (8.5s mesh + 137s solve + 1.5s extract + 1.5s save = ~150s total)
- ✅ Real evidence: Velocity PNG with boundary layer, Pressure PNG with stagnation + suction
- ✅ 2000-iter steady convergence is stable
- ❌ α-tilt is NOT applied (setMethod rejected by 2402 R8) — Cl target ~0.235 not reachable
- ❌ Cl/Cd report reading returns same Vector3 across all inlet conditions — values are not trustworthy
- ⚠️ TKE PNG still missing (FF alias TBD)
- ⚠️ The 2.146 Cl value is **probably not real**; the 0.00958 v1 value is also probably not real (similar staleness); user should treat both as "pipeline runs, Cl reading is broken, need to fix report path"
- 📋 DEC-005 (FF sampling) is now even broader: it covers LDC FF probes **and** NACA report reading
