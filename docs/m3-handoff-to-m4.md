# M3 → M4 Hand-off

**Date:** 2026-06-13
**From:** M3 (CST + FFD + 100 STLs) — DONE
**To:** M4 (Solver runs on 100 STLs + surrogate training data assembly)
**Status:** Ready for handoff. 100/100 watertight STLs available at
`stl_samples/stl/`, LHS coefficients at `stl_samples/lhs/`.

---

## 1. What M3 delivered (input to M4)

| Artifact | Path | Used by M4 as |
|---|---|---|
| 100 STLs | `stl_samples/stl/r37_lhs_*.stl` | solver input geometry |
| Manifest | `stl_samples/stl/manifest.json` | per-sample CST coeffs + mesh stats |
| LHS samples | `stl_samples/lhs/lhs_samples.npy` | (N=100, 12) design space samples |
| LHS metadata | `stl_samples/lhs/lhs_samples.json` | bounds, seed, method |
| Baseline STLs | `scripts/m3_r37_baseline.stl` | sanity / regression check |

M4 can either:
- (a) loop over the 100 STLs in `stl_samples/stl/` directly (recommended),
- (b) regenerate them from `stl_samples/lhs/lhs_samples.npy` if M3 changes.

## 2. M4 entry points — what to call

```python
# All imports via cfd_harness
from cfd_harness.surrogate.cst import CSTAirfoil
from build_r37_from_cst import build_watertight_stl
import numpy as np, json

samples = np.load('stl_samples/lhs/lhs_samples.npy')      # (100, 12)
manifest = json.load(open('stl_samples/stl/manifest.json'))

for i, coeffs in enumerate(samples):
    mesh = build_watertight_stl(coeffs)                   # watertight
    # Solve with STAR-CCM+ 2402 R8 / OpenFOAM:
    #   pressure_ratio, eta_is, mass_flow = solve(mesh)
    # Append to manifest[i]['solver_result']
```

## 3. M4 deliverables (output expected by M5)

| Deliverable | Path | Format |
|---|---|---|
| 100 solver runs | `m4/runs/rotor37_lhs_*.{sim,foam,csv}` | solver-native |
| Solver results joined | `m4/results/solver_results.csv` | one row per LHS sample |
| Solver results rich | `m4/results/solver_results.json` | manifest joined |
| Mesh quality report | `m4/results/mesh_quality.csv` | y+, max aspect, etc. |
| Surrogate training data | `m4/results/training_data.{npz,csv}` | (X=coeffs, y=solver_outputs) |

## 4. Open questions for M4 — decisions to ratify before kickoff

### Q1. Solver: STAR-CCM+ 2402 R8 or OpenFOAM?

**Recommendation: prototype STAR-CCM+ 2402 R8 for 10-20 STLs to verify the
pipeline, then evaluate OpenFOAM for the remaining 80-90.**

Rationale:
- 2402 R8 already proven for 1-passage rotor (M2 Rotor37Slice2D.java,
  401 lines, runnable end-to-end with k-omega SST + coupled flow)
- 2402 R8 macro API blockers from M2 (SurfaceRepair / SurfaceMeshToPart)
  still exist — need to verify if `importStlSurface` from a watertight
  mesh bypasses the surface-mesh-to-meshable-part gap
- OpenFOAM would avoid the 2402 R8 API issue but introduces snappyHexMesh
  setup time and OpenFOAM solver expertise (not in current M3 plan)
- M3 deferred the solver decision to M4 — it must be resolved at M4 kickoff

**Fallback if STAR-CCM+ fails again:** OpenFOAM + snappyHexMesh, with
a 1-week prototype cycle for 1 STL to validate the workflow.

### Q2. Mesh strategy: per-STL auto-mesh or template mesh?

**Recommendation: per-STL auto-mesh with a fixed base size and surface
refinement on the airfoil.**

Rationale:
- 100 STLs with different shapes need adaptive meshing
- 2D-slice extrude (M3 current) gives a simple prism — surface mesh on
  the airfoil + 1-2 prism layers + 1 tetrahedral volume = ~50K cells
- Per-STL mesh time ~1-2 min with STAR-CCM+ surface mesher
- Total: 100 STLs * 1.5 min avg = 150 min mesh time + solver time

**Mesh-independence check (M3-S3 deferred to M4):** for 1 STL, do
3-mesh GCI study (50K / 200K / 800K) per Roache 1994 to validate
discretization error < 2%.

### Q3. Operating point: design (100% speed) only, or characteristic map?

**Recommendation: design point (100% speed, 20.93 kg/s) for the first
100-run batch. Sweep (3 speed lines × 5-7 mass flows) deferred to M4+.

Rationale:
- 100 STLs × 1 design point = 100 runs
- 100 STLs × 3 speeds × 5 mass flows = 1500 runs (~7-10 days solver)
- The paper's first contribution is the surrogate itself; characteristic
  map is a "validation against multi-point" extension, not core.

### Q4. Solver output quantities (per design point)

Minimum required for surrogate training:
- `total_pressure_ratio` (target: 2.056 ± 0.05)
- `mass_flow_kg_s` (target: 20.93 ± 0.2)
- `isentropic_efficiency` (target: 0.876 ± 0.01)
- `total_temperature_ratio` (for completeness)

Bonus (free if setup includes the right Field Functions):
- `exit_flow_angle` (validates against Suder 1995 exit flow data)
- `thrust` (for completeness, even though R37 is a compressor not a fan)

## 5. M4 timeline (4 weeks)

**W1 (2026-09-30 — M4 kickoff)**
- Q1 ratified (solver decision)
- 1 STL run end-to-end (geometry import → mesh → solve → CSV report)
- Verify is_watertight STL works with chosen solver's import path

**W2 (2026-10-07)**
- 10-STL batch (STAR-CCM+ if chosen) or full OpenFOAM if migrating
- Per-STL runtime profile (mesh time, solve time, CSV size)
- Identify any 2402 R8 / OpenFOAM path blockers

**W3 (2026-10-14)**
- 50-STL batch (if W2 successful)
- Solver results joined to manifest
- Mesh independence check on 1 STL (GCI 50K/200K/800K)

**W4 (2026-10-21)**
- 100-STL batch complete
- Solver results table published
- M4 → M5 hand-off doc (`m4-handoff-to-m5.md`)
- M5 surrogate training can begin (GP / MDN)

## 6. M3 → M4 risk register

| Risk | Impact | Mitigation |
|---|---|---|
| 2402 R8 can't import watertight STL (M2 gap) | M4 stuck | OpenFOAM fallback (Q1) |
| Mesh time per STL > 5 min (budget blowout) | M4 schedule slip | Coarser base size; template mesh; defer characteristic map |
| Solver runtime per STL > 30 min | M4 schedule slip | Reduce iter count to 2000; coarser mesh |
| 100 STLs x 30 min = 50 hours serial | M4 schedule | Parallel on local cores (8+); reduce to 50 STLs if needed |
| LHS samples produce non-physical airfoils | Surrogate quality | Verify max thickness / camber in M4, flag outliers |

## 7. Cross-references

- M3 roadmap: `reports/research/commercial-fan-prop/planning/m3-cst-ffd-surrogate-roadmap.md`
- M3 design doc: `docs/m3-design.md`
- M2 ground rules: `reports/research/commercial-fan-prop/planning/track-c-deliverable.md`
- Gold standards: `knowledge/gold_standards/rotor37.yaml` (performance),
  `knowledge/gold_standards/rotor37_cst_baseline.yaml` (CST)
- AGENTS.md: `~/.mavis/AGENTS.md` (project conventions)
- L0 autonomy: chief-engineer drives inside the M4 phase, stops at M4
  exit gate (per AGENTS.md §Graduated autonomy, L0 default)
