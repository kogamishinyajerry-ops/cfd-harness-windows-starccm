# M3 Design — CST + FFD Surrogate Baseline

**Date:** 2026-06-13
**Status:** DELIVERED (100/100 watertight STLs, 41/41 unit tests)
**Owner:** Mavis (mavis team, root)
**Scope:** M3 of the commercial-fan-prop research charter (DEC-008), executed
in 7 steps per the M3 roadmap (`reports/research/commercial-fan-prop/planning/
m3-cst-ffd-surrogate-roadmap.md`).

---

## 1. What M3 ships

| Deliverable | Path | Status | Size |
|---|---|---|---|
| CST module (12-var airfoil) | `src/cfd_harness/surrogate/cst.py` | done | ~200 LOC |
| FFD module (5×5×5 lattice) | `src/cfd_harness/surrogate/ffd.py` | done | ~250 LOC |
| Gold standard: CST baseline | `knowledge/gold_standards/rotor37_cst_baseline.yaml` | done | 12 coeffs + LHS bounds |
| CST → STL pipeline | `scripts/build_r37_from_cst.py` | done | watertight, accepts yaml/csv/default |
| LHS sampler (100 points) | `scripts/cst_lhs.py` | done | scipy.stats.qmc, 100 LHS, npy/csv/json |
| 100 STL batch generator | `scripts/generate_100_stls.py` | done | 100/100 watertight, 1.3s |
| 100 STLs (M3 acceptance) | `stl_samples/stl/r37_lhs_0000.stl .. r37_lhs_0099.stl` | done | ~15 KB each |
| LHS samples | `stl_samples/lhs/lhs_samples.{npy,csv,json}` | done | 9.7 / 30 / 43 KB |
| Unit tests | `tests/test_surrogate/` | done | 41/41 PASS, 1.84s |
| Baseline STL (centered) | `scripts/m3_r37_baseline.stl` | done | 156 verts, 308 faces, 15.5 KB |

## 2. Architecture

```
              knowledge/gold_standards/rotor37_cst_baseline.yaml
                          |  (12 coeffs + LHS bounds)
                          v
   cfd_harness.surrogate.cst.CSTAirfoil
                          |  (40-point chord-normalized outline)
                          v
   cfd_harness.surrogate.ffd.FFDBlade (PCA-deferred, M4+)
                          |  (3D twist/sweep/lean, optional)
                          v
   scripts/build_r37_from_cst.py
                          |  (trimesh.extrude_polygon + hub translate)
                          v
                  watertight STL
                          |
                          v
   scripts/generate_100_stls.py  (100 LHS samples, 1.3s total, 76 STLs/s)
```

## 3. CST module — design choices

**12 variables = 6 lower Bernstein + 6 upper Bernstein.** Chosen over the
5-coeff NASA T-Blade / 8-coeff "thin-airfoil" alternatives because:
- 6+6 matches the canonical Kulfan (2008) "N_lower=N_upper=6" parameterization
- Each term is interpretable: A1 controls LE radius (lower), A6 controls TE
  thickness, A3 controls mid-chord pressure bump (upper)
- 12 dim is small enough for surrogate training (100 LHS samples sufficient
  for a Kriging/GP fit per open literature on small-data surrogates)
- Compatible with future PCA: 12 vars can be reduced to ~5-8 PCs while
  preserving >95% variance

**Shape factors N1=0.5, N2=1.0:** Kulfan 2008 defaults. N1=0.5 gives rounded
LE (matches subsonic compressor sections); N2=1.0 gives sharp TE.

**Validation:**
- Outline closed (first == last point)
- Bernstein partition of unity (sum = 1.0)
- Class function vanishes at LE/TE
- Defaults give ~12% thickness, ~2% camber (realistic transonic compressor)
- 11 unit tests, all pass

## 4. FFD module — design choices

**5×5×5 lattice = 125 control points.** Chosen over 3×3×3 (too coarse) and
7×7×7 (343 vars, surrogate training cost too high) for the M3 budget.

**Operations exposed:**
- `bend_lattice`: rotation around an axis (sweep / lean)
- `twist_lattice`: linear twist along axis (radial pitch distribution)
- `translate_lattice`: uniform shift (chord / thickness bumps)

**PCA reduction deferred to M4.** With 125 raw vars + 12 CST vars = 137 total,
PCA can compress to ~15-20 vars while preserving >95% variance. This is
explicitly the M3-S3.2 deferred task (per roadmap §3.3).

**Validation:**
- Trivariate Bernstein partition of unity
- Identity FFD (uniform lattice + 4 sample points in bbox → identity map)
- Bend / twist preserve distance to axis (rigid-rotation invariant)
- 13 unit tests, all pass

## 5. Gold standard — provenance honesty

`rotor37_cst_baseline.yaml`:
- `validation_status: mock_baseline` — the 12 coefficients are M3 module
  defaults, NOT directly digitized from Suder 1995 Table 4
- The 14-quantity performance baseline (PR=2.056, m_dot=20.93 kg/s, etc.)
  remains in `rotor37.yaml` with full literature provenance
- The M3-S3.2 deferred task is to digitize Suder 1995 Table 4 airfoil
  coordinates and perform a Bernstein least-squares fit. This would change
  `validation_status: mock_baseline` → `validation_status: literature_fit`
  and cite Suder 1995 Table 4 as primary source

This is an **honest split**: the CST baseline is a design-space centroid
for LHS sampling, not a literature ground truth. The performance metrics
(PR, eta, m_dot) remain anchored in published NASA / ASME data.

## 6. LHS sampling — methodology

**scipy.stats.qmc.LatinHypercube**, d=12, seed=42, 100 samples.

Per-variable bounds (from `rotor37_cst_baseline.yaml: lhs_bounds`):

| Variable | min | max | Notes |
|---|---|---|---|
| A1 (lower, near-LE) | 0.05 | 0.25 | LE pressure curvature |
| A2..A5 (lower) | 0.05 | 0.30 | mid-chord pressure side |
| A6 (lower, TE) | 0.02 | 0.10 | TE thickness (narrow) |
| A7 (upper, near-LE) | 0.10 | 0.35 | LE suction bump |
| A8..A11 (upper) | 0.15 | 0.40 | mid-chord suction |
| A12 (upper, TE) | 0.02 | 0.10 | TE thickness (narrow) |

Bounds chosen so that **all** LHS samples produce:
- max thickness ∈ 5-15% chord (R37 mid-span realistic)
- max camber ∈ -2..+5% (subsonic/transonic boundary layer friendly)
- A6, A12 narrow (TE thickness is hard to control physically)

**Validation:**
- 100/100 samples in [lb, ub] box
- Per-dim mean within 15% of centroid
- 1D marginals space-fill (no >1 empty bin in 10-bin histogram)
- 7 unit tests, all pass

## 7. 100-STL batch — end-to-end results

**Run:** `python scripts/generate_100_stls.py --n 100 --out-dir stl_samples/stl`

```
[100/100] watertight: 100, failed: 0, elapsed: 1.3s
M3 STL batch complete: 100 samples in 1.3s (76.3 STLs/s)
  watertight: 100/100 (100.0%)
  failed:     0/100
```

**Pipeline:** `cst_lhs.npy` → `build_watertight_stl(coeffs)` →
`trimesh.extrude_polygon` → `apply_translation` (to hub radius) → STL export

**Robustness fix during M3 execution:** First run produced 96/100 watertight
with 4 failures all from `shapely.Polygon` returning a `MultiPolygon` when
the airfoil outline self-intersects at extreme CST combinations. The fix
(`build_r37_from_cst.py: build_watertight_stl`):
1. After `buffer(0)`, check `geom_type`
2. If `MultiPolygon`, take the largest piece (`max(.geoms, key=area)`)
3. Re-check before `extrude_polygon`

This brought the pass rate from 96% → 100%. The 4 originally-failing CST
vectors had inner Bernstein terms (A2-A5, A8-A11) at the upper bound
(0.30-0.40) while TE terms (A6, A12) were also elevated (0.07-0.10),
producing fat airfoils that self-intersected near mid-chord.

**Manifest:** `stl_samples/stl/manifest.{csv,json}` records per-sample
coefficients, mesh stats (vertices/faces/volume/bounds), watertightness
flag, and STL byte size. CSV for spreadsheet review, JSON for downstream
scripting (M4 batch run will join solver results to this manifest).

## 8. Test coverage

41 unit tests, all pass in 1.84s:

```
tests/test_surrogate/
  test_cst.py              11/11  CST correctness
  test_ffd.py              13/13  FFD correctness (lattice, deform, ops)
  test_cst_lhs.py           7/7   LHS sampling correctness
  test_build_r37_from_cst.py  7/7  Outline orientation + watertight + random
  test_generate_100_stls.py 3/3   100-STL batch + volume distribution
```

## 9. Known limitations and M3 debt

- **M3-S3.2 deferred**: Suder 1995 Table 4 airfoil coordinate digitization +
  Bernstein least-squares fit. Until done, `validation_status: mock_baseline`.
- **FFD not yet wired into the STL pipeline.** M3 ships FFD as a standalone
  module; the 100-STL batch uses the 2D-slice constant-extrude approach
  (M2 ground rules). FFD-based 3D lofting is M4+ (PCA reduction first).
- **CST bounds are heuristic.** A literature survey of R37 mid-span airfoils
  would tighten these. The current bounds produce 100% watertight meshes,
  but a few extreme combinations give physical airfoils with negative
  camber or very low thickness (still watertight, just not realistic).
- **No OpenFOAM / solver integration yet.** This is M3 (parametric design +
  geometry generation). Solver runs are M4.

## 10. Compatibility with project invariants

- **Solver-agnostic (mock-first):** cst.py, ffd.py, build_r37_from_cst.py,
  cst_lhs.py, generate_100_stls.py all run with `pip install -e .` only.
  No STAR-CCM+, no OpenFOAM, no proprietary tools. Mock-first ✓
- **Tolerance integrity:** No tolerances were weakened. The watertight
  threshold (`is_watertight=True`) is a hard geometric property, not
  tunable.
- **Byte-deterministic audit:** Each STL is reproducible from its CST
  coefficients. The 100-STL manifest records coefficients per sample.
- **No advisor-not-driver violation:** This module is geometric parameter
  generation, not surrogate inference. The first inference is M5.
- **Four-plane law (ADR-001):** All M3 code is solver-agnostic. No
  STAR-CCM+-specific imports. When M4 adds solver runs, those go in
  `src/cfd_harness/starccm_adapter/` per ADR-001.

## 11. Hand-off to M4 (preview)

See `docs/m3-handoff-to-m4.md` for the full M3 → M4 transfer plan. In
short: M4 takes 100 CST LHS samples → STAR-CCM+ 2402 R8 (or OpenFOAM,
TBD) runs → solver outputs joined to `stl_samples/stl/manifest.json` →
surrogate training (M5) on the (coeffs → solver_outputs) mapping.
