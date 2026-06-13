# DEC-005 — Real-solver field/force read-back is a dead-end on STAR-CCM+ 2402 R8 (19.02.009)

- **Status:** accepted (dead-end documented) — 2026-06-13
- **Supersedes:** the dozens of phantom "DEC-005" cross-references in
  `reports/STATE.md`, `reports/LDC_STATUS.md`, and all `DEC-007-NACA-*`
  files. Until now DEC-005 was cited everywhere but never written.
- **Related:** DEC-003 (LDC exit gate, blocked on this), DEC-007 (NACA
  closed loop), DEC-009 (solver deadlock / Rotor37 hollow-green).

## Context

Two of the project's headline real-solver V&V goals need to read
quantitative data back out of a solved `.sim` through the **public Java
macro API**:

1. **LDC Ghia-1982 centerline tolerance** → needs per-cell field
   sampling of `u`/`v` along the cavity centerlines.
2. **NACA Cl/Cd closed-loop tolerance** (vs Ladson 1988) → needs a
   trustworthy force-coefficient read-out.

This decision records, with evidence, that **neither is reachable on
this STAR-CCM+ build via the macro API**, and reframes the WIN_STARCCM
ceiling accordingly.

## Findings (evidence)

### (a) Per-cell field sampling — CONFIRMED removed
- `star.common.{Probe,PointProbe,LineProbe,SampleProbe,FieldSample}` and
  `ProbeManager` are **all absent from the 2402 R8 classpath**
  (`probe20_probe_objs.log`: "ProbeManager not in classpath"). 20 probe
  macros were tried (`macros/_probes/Probe9..20.java`).
- `PrimitiveFieldFunction.getValue()` is **no-args only** — there is no
  `getValue(coordinate)` overload.
- `VolumeAverageReport` over a **whole region** does work
  (`setFieldFunction` + `getReportMonitorValue`, `probe13_split_ffaverage.log`)
  but returns `-3.04e-17` (≈0) on an uninitialized field, and gives a
  region average — not a per-cell/centerline sample.
- Net: `lid_driven_cavity_u_centerline.csv` is all-null; the Ghia
  tolerance gate cannot be evaluated programmatically.

### (b) Force-coefficient read-out — CONFIRMED broken
- `ForceCoefficientReport.compute()` → `NoSuchMethodException`.
- `ForceCoefficientReport.getValue()` returns a `Vector3` whose fields are
  `x/y/z`; `NacaTrueE2E.java` blindly assumes that maps to `[Cd, Cl, Cm]`.
  The values are **bit-identical across 10 vs 15 m/s and α = 0° vs 4°**
  → stale-cached / sentinel, not a real read.
- `SurfaceIntegralReport` is found and binds to the airfoil but
  `getValue()` returns `null` (no compute path).
- The current artifact `D:\StarCCM Codebuddy\Cases\Results\naca2412_summary.json`
  reports **Cl=8.52, Cd=−0.41, run_ok=true** — physically impossible
  (a 2D airfoil cannot have Cl=8.5, and Cd<0 is negative drag).

## Decision

Real-solver **quantitative** V&V (LDC Ghia centerline, NACA Cl/Cd
tolerance) is **UNREACHABLE on STAR-CCM+ 2402 R8 / 19.02.009 via the
public Java macro API.** Stop spending Java-side effort trying to read
these back — the search is exhausted (20 probes + the 1623-line
`NacaTrueE2E.java` + 9 `DEC-007` versions all confirm it).

The **WIN_STARCCM executor ceiling is reframed to "qualitative /
pipeline-verified"**: a real run is trusted to *spawn → import → mesh →
solve → save .sim → render scene PNGs → report region averages*, but is
**never** claimed to pass a literature tolerance gate. This mirrors the
MOCK `WARN` ceiling: real-solver runs are not `validation_status:
validated` until a quantitative path exists.

### The only quantitative paths (both out of the macro API)
- **(a) GUI export** — open the already-solved `.sim` in the STAR-CCM+
  GUI, export a surface-Pressure / centerline CSV, read it in Python.
  Highest ROI; requires a human GUI session (cannot be automated
  headless here). For NACA, `naca2412_v35_true.sim` (115 MB, solved) is
  ready for this.
- **(b) Build upgrade** — a STAR-CCM+ build that re-exposes
  `ProbeManager` and/or a working `ForceCoefficientReport`.

## Consequences (harness actions taken)

- **Fail-closed plausibility gate** added to the adapter
  (`src/cfd_harness/starccm_adapter/executor.py`,
  `_build_macro_run_report`): force coefficients that are physically
  impossible (`|Cl|>3`, `Cd<0`) or a `run_ok=false` summary are
  **quarantined** (`force_coefficients_quarantined`) and force
  `ExecutionResult.success=False` + `summary_plausible=False` — the
  adapter can no longer launder a sentinel summary into a success. Mock
  tests: `tests/starccm_adapter/test_macro_outputs.py`.
- **STATE.md "covered" map** must read LDC / NACA / cylinder as
  *pipeline-verified*, not *tolerance-validated*. The `✓` glyph means
  "spawns + solves + saves", not "passes a gate".
- **DEC-003 (LDC exit gate) stays blocked** on this until a GUI export
  or build upgrade lands.

## Follow-ups
- Run the GUI surface-Pressure CSV export on `naca2412_v35_true.sim` to
  obtain one trustworthy quantitative Cl/Cd datapoint (manual; user GUI
  session).
- (Sibling repo) make `NacaTrueE2E.java` itself fail closed: stop
  emitting `run_ok=true` with sentinel Cl/Cd, and fix the case_id
  mislabel (`naca0012_airfoil` on 2412 geometry).
