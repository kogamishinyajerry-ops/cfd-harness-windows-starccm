# DEC-005-R1 — Force & point-field read-back are RECOVERED on STAR-CCM+ 2402 R8 (clean single-region sim)

- **Status:** accepted (revises DEC-005) — 2026-06-15
- **Revises:** [DEC-005](DEC-005-ff-sampling-report-reading-deadend.md) — its
  conclusion "real-solver quantitative read-back is UNREACHABLE via the public
  Java macro API" is **partially overturned**. DEC-005 stays on record as an
  honest account of the *historical* dead-end; this revision documents that the
  dead-end was a **sim-setup / parts-binding bug**, not a fundamental API limit.
- **Related:** DEC-003 (LDC exit gate — now unblockable via LinePart sampling),
  DEC-007 (NACA closed loop — re-attemptable with clean binding), DEC-009.

## Context

DEC-005 declared two read-back paths dead on 2402 R8 / 19.02.009:
(a) per-cell / centerline **field sampling** (ProbeManager removed), and
(b) **force-coefficient** read-out (bit-identical sentinel `Vector3`). That
conclusion was drawn from the NACA pipeline (`NacaTrueE2E.java`) and 20 probe
macros — all run against **broken or multi-region sims**, some with no real
flow (zero solution), and force reports bound by a *heuristic* ("the region's
`Default Boundary`").

While quantitatively validating the cylinder wake (Kármán vortex street) on a
**clean single-region sim** (`D:\StarCCM Codebuddy\Cases\cyl_vortex_clean.sim`,
251 644-cell quasi-2D slab, real developing shedding), both read-back paths
turned out to **work**. This revision records the evidence and the correct API.

## Findings (evidence)

### (b) Force read-back — WORKS (was a boundary-binding bug)
- **Correct class is `star.flow.ForceReport`** (and `star.flow.ForceCoefficientReport`).
  `star.base.report.ForceReport` → `ClassNotFoundException`. Older macros used
  `import star.flow.*` + the unqualified name, masking the package.
- On the clean sim the cylinder wall is an explicitly **named** boundary
  (`cylinder`, `WallBoundary`, nonzero faces). The old sims bound the report to
  an empty **`Default Boundary` (0 faces)** → the surface integral saw no faces
  → returned exactly `0.0`. *That* is the "sentinel zero", not an API limit.
- `report.setObjects([cylinder])` + read `getReportMonitorValue()` →
  **real nonzero live force**. At t=4.81 s: `Fx (lift)=2.36e-5 N`,
  `Fz (drag)=1.93e-4 N` → instantaneous **Cd = 1.30** (textbook for Re≈1700).
- `report.getValue()` returns `star.common.Vector3` = the **full live force
  vector** `[Fx, Fy, Fz]`; its components **change over time** (lift oscillates
  ±0.48 in `C_L` at the shedding frequency). It is NOT stale-cached. (The NACA
  "bit-identical across 10/15 m/s, 0°/4°" was the wrong-boundary / zero-flow
  artifact.)
- **Direction API gotcha:** `getDirectionInput().setVector(...)` is *silently
  ineffective* (back-reads unchanged `[1,0,0]`). The working setter is
  **`report.getDirection().setComponents(dx,dy,dz)`** (the `VectorPhysicalQuantity`).
  Default direction is already `(1,0,0)`, so a default-direction force report's
  `getReportMonitorValue()` already returns `Fx`.

### (a) Point/line field sampling — WORKS via derived parts (not ProbeManager)
- ProbeManager is indeed gone, but **`PartManager.createPointPart(Vector regions,
  DoubleVector coords)`** creates a derived point part (`star.vis.PointPart`;
  `DoubleVector extends java.util.Vector`, coords in metres). A `MaxReport` over
  that single-point part + `getReportMonitorValue()` returns the **real field
  value at that point**.
- Verified: a probe at wake point `(0, 0, 0.10)` read `ux=-0.47 m/s`,
  `uz=0.39 m/s` (matches the solved field), and a per-time-step `ReportMonitor`
  on it captured the lateral-velocity history cleanly (±0.48 m/s, 4 shedding
  cycles).
- `createLinePart(...)` and `createPointsFromTable(...)` also exist → the **LDC
  Ghia centerline** is reachable the same way (LinePart + per-point reports or
  an XYZ-table export), without ProbeManager.

### Cross-validation that the reads are physically real (not just nonzero)
- St from **wake velocity** FFT = 0.232; St from **wall lift** FFT = 0.230 →
  two independent signals agree to **0.6 %**, and lift oscillates at `f` while
  drag oscillates at `2f` (classic shedding signature). Cd_mean = 1.198 (±0.13)
  vs subcritical experiment ≈1.1 → 8.9 %. These would be impossible if the
  reads were sentinels.

## Decision

DEC-005's blanket "UNREACHABLE via the macro API" is **REVISED**. On
STAR-CCM+ 2402 R8, quantitative read-back **IS reachable from the public Java
macro API** when:

1. the case is a **clean single fluid region** (no leftover empty boundaries /
   region confusion), and
2. the force-integration boundary or the field-sample part is **correctly
   identified** — a named wall with nonzero faces (force) / a derived
   `PointPart`/`LinePart` (field) — and
3. the **correct APIs** are used: `star.flow.ForceReport` +
   `getDirection().setComponents(...)` for force; `PartManager.createPointPart`
   + `MaxReport.getReportMonitorValue()` for point fields.

The **WIN_STARCCM executor ceiling is lifted from "qualitative only" to
"quantitative where region/boundary/part binding is clean."** A real run on a
clean single-region case may now be compared against a literature tolerance gate.

## Consequences

- The cylinder case `circular_cylinder_wake` now reports **St + Cd_mean + Cl_rms
  all measured**, verdict **PASS (2D)**: St=0.232 (vs 0.21, +10.5 %) ✅,
  Cd_mean=1.198 (vs 1.1, +8.9 %) ✅, Cl_rms=0.264 ⚠️ (over-predicted ~2× — a
  **known quasi-2D URANS limitation**, no spanwise decorrelation; this is a
  model-fidelity caveat, not a read-back failure).
- **DEC-003 (LDC Ghia gate) is unblocked in principle** — sample the centerlines
  with a `LinePart` + reports on a clean cavity region.
- **NACA Cl/Cd is re-attemptable** — bind `star.flow.ForceCoefficientReport` to
  the correctly-named airfoil wall in a clean single-region sim (the historical
  failure was wrong-boundary binding + zero/implausible solution).
- The **fail-closed plausibility gate stays** (`executor.py`,
  `force_coefficients_quarantined`): real-but-wrong reads (empty boundary → 0,
  divergent solution) must still be caught; "readable" ≠ "always trustworthy".
- Honesty ceiling unchanged in spirit: a number is `validated` only when it both
  reads correctly **and** lands inside the literature tolerance for the regime.

## Evidence artifacts / reproduction

- Macros (sibling `D:\StarCCM Codebuddy\macros\`, not in this repo):
  `VortexLiftProbe.java` / `VortexLiftProbe2.java` (force read + direction-API
  diagnostics), `VortexLiftHistory.java` (lift+drag+velocity histories),
  `VortexStrouhal.java` + `StrouhalIntrospect.java` (point-probe St).
- In-repo analysis/report: `scripts/strouhal_analysis.py`,
  `scripts/strouhal_crossval.py`, `scripts/vortex_report.py` →
  `卡门涡街_后处理报告.html`.
- Data: `Cases/Results/strouhal_*.csv`, `lifthist_*.csv`,
  `strouhal_result.json`, `strouhal_crossval.json`.

## Follow-ups

- Port the clean-binding pattern to **LDC** (LinePart centerline) and **NACA**
  (single-region force-coefficient) to convert their pipeline-verified status to
  tolerance-validated.
- Update `reports/STATE.md`: the `✓` for `circular_cylinder_wake` is now
  *tolerance-validated (2D)*, not merely *pipeline-verified*.
- Lengthen the sampling window / run a mesh-convergence (GCI) pass to tighten the
  Cl_rms statistic and quantify the quasi-2D over-prediction.
