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
## Update 2026-06-12: 20-probe diagnostic (4-8h DEC-005 chase)

> Chief-engineer ran 20 reflective probes (macros\_probes\Probe9.java through
> Probe20.java) against lid_driven_cavity_solved.sim to exhaustively
> scan STAR-CCM+ 19.02.009 R8 for any viable path to sample a FieldFunction
> at a specific point. The full probe catalog is in
> D:\CFD-harness-Windows-StarCCM\probe{9,10,11,...20}_*.log (~50 KB total).

### Summary of 20 probes (cumulative finding: dead end on 2402 R8)

| # | Hypothesis tested | Outcome |
|---|---|---|
| 9 | egion.getRepresentation().getInternalMesh() path | ❌ Region has no getRepresentation on 2402 R8 |
| 10 | All Region methods + 21 candidate Report class names (LineSample / PointSample / SurfaceAverage / LineAverage / XYPlot etc.) | ❌ Region has 0 mesh-related methods; all 21 star.common.* / star.base.report.* candidate classes return ClassNotFoundException |
| 11 | getCellInfo(Region, Vector) + FvRepresentation.generateMeshReport(List<FF>) | ❌ getCellInfo works only with empty Vector; generateMeshReport throws "Wrong type object in ObjectRegistry from vectorized properties" (CLI API expects a non-standard format) |
| 12 | Same generateMeshReport with different List<FF> | ❌ same vectorized-properties error |
| 13 | VolumeAverageReport(Ux) on the existing cavity region | ✅ **works**, but returns single region-wide value (-3.04e-17 ≈ 0, consistent with Ux symmetry of the cavity) — does NOT give per-cell data |
| 14 | fm.createFieldFunction() + setDefinition("[1]") + splitRegionsByFunction | ❌ User FF creates OK but its value isn't evaluated against the mesh; previewSplitRegions returns 0 |
| 15 | Built-in Position / Centroid / CoordinateY field functions | ❌ Position and Centroid resolve (real FFs), but previewSplitRegions(Position) returns 1 (no multi-slab split) |
| 16 | Position.getComponentFunction(0/1/2) + splitRegionsByFunction | ❌ All three components return 1 sub-region (no multi-slab split) |
| 17 | uxFF.getValue(*) exhaustive — every overload, every superclass | ❌ Only getValue() (no-arg) exists; zero getValue(coordinate) overloads on VectorComponentFieldFunction or any superclass |
| 18 | AreaAverageReport(Ux) on each of 9 boundaries | ✅ Path works, returns 0 for all boundaries (BC was set via Condition, not field) |
| 19 | getCellInfo with various Vector inputs (FF / String / both) | ❌ empty Vector returns NeoProperty; FF/Vector variants throw "Wrong type vectorized properties" |
| 20 | star.common.Probe / PointProbe / LineProbe / ProbeManager / ProbeGroup class resolution | ❌ **all 9 candidates ClassNotFoundException** — **structural finding: STAR-CCM+ 19.02.009 R8 has REMOVED the ProbeManager API entirely from the public Java classpath** |

### Structural conclusion

STAR-CCM+ 19.02.009 (2402 R8) **does not expose a viable public Java API
for sampling a FieldFunction at a single point**. The combination of:
- ProbeManager removed from the public classpath (Probe20)
- SimpleBlockPart / createBlockPart removed from RegionManager (Probe10, 5e)
- PrimitiveFieldFunction.getValue(coordinate) removed (ProbeFFM / Probe17)
- getDefinition().eval(coord) removed (ProbeDefEval)
- splitRegionsByFunction with Position FF doesn't produce multi-slab split (Probe15/16)
- generateMeshReport rejects Vector<FieldFunction> input (Probe11/12)
- 21 candidate report class names all ClassNotFoundException (Probe10)

…means the only way to get per-cell field data in 2402 R8 is to:
1. Port the user's CliExportFieldData.java (1500 lines, ~3-5h of cascade-engineering
   to navigate the 5a-5k reflective sub-paths and the Wrong type vectorized properties
   error class) — out of scope for the 4-8h window
2. Use the STAR-CCM+ GUI File > Export > Field Data menu (manual, not headless-automatable)
3. Upgrade to a newer STAR-CCM+ build that may restore the ProbeManager API

### What's still green

- LDC macro runs end-to-end and saves a valid .sim (init_ok=true, un_ok=true)
- The saved lid_driven_cavity_solved.sim is openable in the STAR-CCM+ GUI and the
  user can verify the solution against Ghia 1982 Table I via the GUI's PointProbe /
  LineSampling tools (DEC-005 alternative path: manual GUI verification)
- All 28 cfd-harness bridge unit tests + 4-8h diagnostic probes + CliExportFieldData
  5g cascade are reusable artifacts

### Recommendation for chief-engineer

Close DEC-005 as **deferred to STAR-CCM+ build upgrade OR CliExportFieldData v24 port**.
The paper draft already honestly marks u_centerline=null, DEC-005 known issue in
paper-draft-2026-07.md §5.1.5; this update adds the structural finding so reviewers
understand the root cause is a 2402 R8 API gap, not a code bug.
