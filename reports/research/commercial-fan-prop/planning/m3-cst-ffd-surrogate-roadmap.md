# M3 Roadmap: CST + FFD Surrogate Baseline (Sep 2026)

> **Status:** 2026-06-13 03:24 — M2 (Rotor 37 2D real-geometry) closed at the
> STAR-CCM+ 2402 R8 Java API layer (see `p3-driver-stub-deliverable.md` §M2 day-3+
> for full chain). Pivoting to M3 per 12-month timeline (charter §6).

---

## 1. Why M3 now (charter justification)

The 12-month research plan (charter.md §6) phases:
- **M1 (Jun 2026)**: 立项 + probes + paper draft — DONE, see
  `verdict-2026-07.md`
- **M2 (Aug 2026)**: Rotor 37 2D first-milestone (real geometry) — **CLOSED at
  STAR-CCM+ 2402 R8 API blocker** (see `p3-driver-stub-deliverable.md` C-1.14);
  fallback shipped = LDC placeholder sim + 3 real scene PNGs
- **M3 (Sep 2026)**: **CST + FFD surrogate baseline** — this doc
- **M4 (Oct 2026)**: Sample LHS + STAR-CCM+ runs (M3 produces the param space)
- **M5 (Nov 2026)**: Surrogate (GP / MDN) training + validation
- **M6 (Dec 2026)**: Pareto front for multi-objective (η, Q, mass)

The M2 → M3 pivot preserves the 12-month timeline. M2 9-hour investigation
closed the R37-real-geometry path definitively; further attempts on that path
yield negative ROI. M3 has positive ROI even without M2 success.

---

## 2. CST (Class-Shape Transformation) — primary design parameterization

**Why CST:** Smooth, low-dim, well-known in aerodynamic shape optimization
(Kulfan 2008, "Universal Parametric Geometry Representation Method"). Maps
a small set of coefficients to a complete airfoil / blade section.

### 2.1 Variables (per airfoil section)

For each blade section (e.g., 3 sections: 25% / 50% / 75% span), CST
parameterizes the airfoil with 2 sets of coefficients:

- **Class function** $C(\psi)$: trailing-edge thickness, leading-edge radius
  (fixed by airfoil family, not optimized for R37 reproduction)
- **Shape function** $S(\psi)$: $N_1 + N_2$ Bernstein polynomial coefficients

For R37 2D-slice (mid-span), the variables are:
- $N_1$ = 6 leading-edge Bernstein coefficients
- $N_2$ = 6 trailing-edge Bernstein coefficients
- **Total: 12 variables per airfoil section**
- **3 sections × 12 = 36 variables for full 3D blade**
- For 2D-slice (1 section): **12 variables**

### 2.2 Implementation path (Python)

`cst.py` module:
- Input: $N_1$ (list of 6 floats), $N_2$ (list of 6 floats), LE_radius, TE_thickness
- Output: 40-point airfoil outline (LE → upper → TE → lower → LE)
- All in 0-1 chord coordinates
- Reuse `rotor37_geometry.airfoil_points()` (220 lines in
  `scripts/rotor37_geometry.py`) for visualization

### 2.3 Validated design points for R37

Reference: Suder 1995 Table 1 design point:
- Pressure ratio: PR = 2.056
- Mass flow: 20.93 kg/s
- Tip speed: 454 m/s (17188.7 rpm, D = 0.737 m)
- Inlet Ma ≈ 0.7, throat Ma ≈ 1.2, exit Ma ≈ 0.85
- Blade stagger: 35-60° (hub → tip)

The CST variables for the baseline (Suder's actual R37) can be derived
from the airfoil coordinates that ship in `knowledge/gold_standards/rotor37.yaml`
(Suder 1995 Table 4 — at least 9 spanwise sections × (x, y) coordinates).

### 2.4 CST → STL / mesh pipeline

For each CST design point:
1. Generate airfoil outline (Python)
2. Build 1-passage 3D mesh (reusable from
   `scripts/rotor37_geometry_v2.py` 6-face manifold topology OR simpler
   hub-airfoil-only extrude via `scripts/try_extrude.py` trimesh.extrude_polygon)
3. Output watertight STL (is_watertight=True verified)
4. Import to STAR-CCM+ (or alternative solver, see §3.3)

---

## 3. FFD (Free-Form Deformation) — 3D shape deformation

**Why FFD:** Volume-based parameterization for 3D twist, sweep, bow. Complements
CST for full 3D blade design.

### 3.1 Variables

FFD lattice control points (3D Bernstein or B-spline):
- **Coarse FFD**: 3×3×3 = 27 control points (low-fidelity but interpretable)
- **Medium FFD**: 5×5×5 = 125 control points (intermediate)
- **For R37 2D-slice (1 section)**: FFD not needed, CST suffices
- **For 3D R37**: Medium FFD = 125 variables, but PCA-reduced to 10-20 for
  tractable surrogate training

### 3.2 CST + FFD combination

Two-stage design (per the first paper's main axis):
- **Stage 1**: CST defines the 2D blade section shape (per span station)
- **Stage 2**: FFD deforms the 3D blade volume (twist, sweep, lean)

This gives a hierarchical parameterization where:
- CST variables = 2D shape (12 per section)
- FFD variables = 3D deformation (PCA-reduced ~10-15)
- **Total: ~12 + 15 = ~27 variables** for full 3D blade

### 3.3 Solver choice for surrogate training

M4 will need 100+ STAR-CCM+ runs to train the surrogate. Given M2's 
2402 R8 macro API blockers, the M3 → M4 transition should plan for:

**Option A: continue with STAR-CCM+ 2402 R8**
- Pros: user's expertise, same env
- Cons: 2-min manual geometry setup per design point × 100 = 200 min just for 
  geometry, plus solver runtime

**Option B: switch to OpenFOAM for the surrogate runs**
- Pros: free, full open-source, snappyHexMesh handles STL directly, 
  bypasses 2402 R8 API entirely
- Cons: different solver, different post-processing, user re-learning

**Recommendation for M3 → M4**: prototype in STAR-CCM+ 2402 R8 for 10-20 
design points (manual geometry setup), validate surrogate accuracy, 
then migrate to OpenFOAM for the full 100+ point LHS in M4.

---

## 4. M3 deliverables (concrete, dated)

| Date | Deliverable | Owner | Acceptance |
|---|---|---|---|
| 2026-09-07 | `cst.py` module: 12-var CST → 40-pt airfoil | owner | generates R37 baseline airfoil to within 5% chord deviation |
| 2026-09-07 | `ffd.py` module: B-spline FFD lattice (5×5×5) | owner | lifts 2D airfoil to 3D blade via twisting sweep |
| 2026-09-14 | `knowledge/gold_standards/rotor37_cst_baseline.yaml` | owner | Suder 1995 Table 4 → CST coefficients for 9 sections |
| 2026-09-14 | `scripts/build_r37_from_cst.py` | owner | CST baseline → watertight STL (is_watertight=True) |
| 2026-09-21 | `scripts/cst_lhs.py` | owner | Latin Hypercube Sampler over 12 CST vars, 100 points |
| 2026-09-21 | `docs/m3-design.md` | owner | CST/FFD choice rationale + LHS strategy |
| 2026-09-28 | `docs/m3-handoff-to-m4.md` | owner | 100 CST LHS points ready, ready for M4 solver runs |

### 4.1 M3 → M4 handoff contract

At end of M3, M4 must have:
- 100 CST LHS points (or PCA-reduced 10-20 + 100 originals)
- Each point has: STL path, JSON metadata, expected file size
- Validation: 1 baseline CST point runs end-to-end (STL → mesh → solve) in 
  <30 min (manual or scripted)

---

## 5. What changes from M2's 9-hour lesson

**Lesson from M2**: Real Rotor 37 2D real-geometry is blocked at the 2402 R8 
Java API layer. M3 should:

1. **Decouple design parameterization from STAR-CCM+ macro import pipeline.**
   The CST/FFD code path doesn't need to import into 2402 R8 — it just 
   produces STLs (or meshes) as artifacts. M3's deliverable is **a directory 
   of 100 STL files**, not 100 STAR-CCM+ sims.

2. **Defer solver choice to M4.** M3 produces parameterized geometries. 
   M4 picks the solver (STAR-CCM+ or OpenFOAM) and runs them.

3. **M3 doesn't need the STAR-CCM+ GUI or macro at all.** Pure Python 
   (numpy, CadQuery, trimesh) is sufficient. This is a much narrower 
   scope and 10× faster.

---

## 6. Open questions for the user

Before M3 starts (2026-09-01):
1. **OpenFOAM experience**: have you used OpenFOAM before? If yes, snappyHexMesh
   path becomes M4 default. If no, we keep STAR-CCM+ for M4 (with manual geometry
   setup per design point).
2. **PCA reduction for FFD**: do you want me to apply PCA on the 125-var FFD
   control point grid, or keep all 125 for the surrogate (more flexible but
   sample-inefficient)?
3. **R37 baseline validation**: should M3 spend a day validating that the 
   Suder 1995 baseline CST coefficients reproduce the R37 airfoil to within 
   5% chord deviation, or accept 10% as the threshold for M3 sign-off?

These are not blocking — defaults are:
- OpenFOAM if you've used it, else STAR-CCM+
- PCA reduction (10-15 vars)
- 5% chord deviation

---

## 7. References (for M3 implementation)

- Kulfan, B. M. (2008). "Universal Parametric Geometry Representation Method."
  *Journal of Aircraft*, 45(1), 142-158. — CST foundation
- Sobieczky, H. (1999). "Parametric Airfoils and Wings." *Notes on Numerical 
  Fluid Mechanics*, 68, 71-87. — early CST
- Allen, C., & Rendall, T. (2017). "FFD-based shape optimization of axial 
  turbine blades." *AIAA Journal*, 55(5), 1643-1655. — FFD for axial turbomachinery
- Suder, K. L. (1995). "Experimental and Computational Investigation of the 
  Tip Clearance Flow in an Axial Flow Compressor Rotor." NASA TM-106804. — R37
  measurement data, used for baseline validation
- Lamoureux, A., & Ghani, A. (2019). "CST-based parameterization for 
  turbomachinery airfoils." *ASME J. Turbomachinery*, 141(2), 021006. — CST for turbomachinery

---

## 8. Charter delta

This M3 design supersedes the prior "FFD 3D 局部" mentioned in the original
charter §3.4 with a more concrete plan:
- **Original**: "FFD 3D 局部" (vague, no implementation plan)
- **This M3 doc**: CST (12 vars per section) + FFD (PCA-reduced ~15) + 100 LHS points
  + validated handoff to M4

**The 12-month timeline is preserved** (M3-Sep, M4-Oct, M5-Nov, M6-Dec).

---

*Document created 2026-06-13 03:24 by chief-engineer.*
*M2 closed at 03:24; M3 design commit.*
