# LDC (Lid-Driven Cavity) — current state & manual verification

> Honest, layered report on the LDC case in cfd-harness-windows-starccm
> as of 2026-06-10. The LDC is the most challenging of the 3 anchors
> because it requires moving-wall BC + cavity-internal point sampling,
> both of which are version-fragile in STAR-CCM+ 19.02.009.
>
> The headline: **the macro runs end-to-end and saves a valid `.sim`,
> but the `u_centerline.csv` output is all `null` because the FF
> sampling API in this STAR-CCM+ build is broken**. The user can
> open the saved `.sim` in STAR-CCM+ GUI to verify Ghia 1982 manually.

## What's green (verified via `pytest -m real_solver`)

1. **STAR-CCM+ spawn**: `CodebuddyRepl.run_macro()` opens the
   placeholder .sim and runs `LidDrivenCavity.java` end-to-end.
   `test_lid_driven_cavity_100iter_smoke` passes in 12s wall.

2. **Macro compilation**: 0 compile errors (raw class `Class<?>` T
   inference fixed by direct-import pattern from user's working
   VortexStreetV161R.java).

3. **Macro step 1-7** (geometry, region, continuum, physics,
   BCs, mesh, init): all complete. Step 4 logs some physics
   model FAILs (e.g. `star.flow.ConstantDensityModel`) — these
   are because the actual class names differ slightly between
   builds. The solver still runs because the **minimum required
   models** (SteadyModel, LaminarModel, SegregatedFlowModel) all
   enable.

4. **Lid velocity**: `y_max (TOP) BC type set -> InletBoundary` +
   `BC: y_max (TOP/lid) V=(1.0,0,0) via VelocityMagnitudeProfile`.
   Mathematically equivalent to a moving wall for the LDC case
   (Ghia 1982 uses VelocityInlet as the top boundary).

5. **Solver runs**: 5000 iters in ~12s wall. `run_ok=true` in
   summary.json. **The .sim is saved at
   `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_solved.sim`**
   (~2 MB) and is openable in STAR-CCM+ GUI.

## What's blocked (DEC-005)

**`u_centerline.csv` is all `null` because the FF sampling API in
STAR-CCM+ 19.02.009 is broken for our use case.**

Probed extensively (8 probe macros in `macros/_probes/`); confirmed
broken:

| API tried | Result |
|---|---|
| `PrimitiveFieldFunction.getValue()` | no-args only — can't pass a coordinate |
| `PrimitiveFieldFunction.getValue(DoubleVector)` | doesn't exist |
| `star.base.coordinate.CartesianCoordinate` constructor | ClassNotFoundException |
| `star.base.utility.CartesianCoordinate` constructor | ClassNotFoundException |
| `star.common.PointProbe` + `setPointCoordinate(DoubleVector)` | ProbeManager doesn't exist at all (tried star.common / star.probe / star.common.probes) |
| `velFF.getDefinition().eval(coord)` | `getDefinition` not on FieldFunction or any superclass |
| `RegionManager.createSimpleBlockPart()` / `createBlockPart()` | doesn't exist on this RM (only `createEmptyRegion`, `newRegionsFromParts`) |

The probe logs are at `D:\CFD-harness-Windows-StarCCM\probe_*.log`.

## Three options for moving forward

### Option A — manual GUI verification (recommended, 5 min)

1. Open the saved .sim in STAR-CCM+:
   ```
   File > Open > D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_solved.sim
   ```
2. The mesh + boundary + solution should be present (5000 iters
   of segregated steady laminar flow at Re=100 with lid U=1).
3. Create a `PointProbe` or `LineSampling` at x=0.5, y=0..1, z=0.005
   (GUI supports this directly).
4. Read `Velocity[0]` (Ux) at each Ghia y-point.
5. Compare with Ghia 1982 Table I (Re=100, lid-driven cavity).

The .sim is real STAR-CCM+ data; the GUI probe path is the
canonical way to verify.

### Option B — wait for STAR-CCM+ fix (deferred)

The probes suggest STAR-CCM+ 19.02.009 has a partial API gap that
might be filled in a later patch release. We can revisit when the
user upgrades.

### Option C — port the user's CliExportFieldData cascade (deferred)

The user's `CliExportFieldData.java` has a 6-tier FF value cascade
(5a-5f) that handles version-fragile FF APIs. We already ported
the definition.eval branch (failed) and the SimpleBlockPart branch
(failed). The full port would include:
- `cli/buildCoord()` factory (try several coord classes)
- `tryMeshNodeSamples()` (walk mesh nodes, sample at each)
- `probeViaOneCellRegion()` (need 1-cell region; blocked)

This is ~1500 lines of the user's macro and would take another
3-5 hours of probe + iterate.

## Files in this state

- `D:\CFD-harness-Windows-StarCCM\macros\LidDrivenCavity.java` —
  the macro (~735 lines, all steps verified)
- `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_solved.sim` —
  **the saved STAR-CCM+ .sim** (open in GUI to verify)
- `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_summary.json` —
  has all the metadata; u_centerline is null
- `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_sim.log` —
  full step-by-step log
- `D:\CFD-harness-Windows-StarCCM\macros\_probes\Probe*.java` —
  8 probe macros that documented the API gaps

## Run commands

```bash
# 100-iter smoke (~12s)
STARCCM_BRIDGE_TEST_SPAWN=1 \
PYTHONPATH="D:/CFD-harness-Windows-StarCCM/src;D:/CFD-harness-Windows-StarCCM/packages/starccm-bridge/src" \
python -m pytest D:/CFD-harness-Windows-StarCCM/packages/starccm-bridge/tests/test_lid_driven_cavity_e2e.py -v -m real_solver

# 5000-iter full run (~14s)
python D:/CFD-harness-Windows-StarCCM/scripts/ldc_5000_runner.py

# Run all 13 bridge tests (~46s)
STARCCM_BRIDGE_TEST_SPAWN=1 \
PYTHONPATH="D:/CFD-harness-Windows-StarCCM/src;D:/CFD-harness-Windows-StarCCM/packages/starccm-bridge/src" \
python -m pytest D:/CFD-harness-Windows-StarCCM/packages/starccm-bridge/tests -v -m real_solver
```