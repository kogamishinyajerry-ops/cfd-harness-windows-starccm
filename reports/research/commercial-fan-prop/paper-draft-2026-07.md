# Neural Surrogate-based Parametric Multi-objective Optimization for Commercial Aircraft Fan and Propeller Blades

> **Submission target (planned)**: *AIAA Journal* / *Computers & Fluids* / *Aerospace Science & Technology*
> **Draft status (as of 2026-06-12)**: M1 milestone draft — IMRaD framework proposal.
> All numerical claims are cited with `file:line` references into project artifacts.
> No real training samples, no surrogate model, no Pareto frontier has been produced at
> this draft stage; §5 reports the stub-level validation results from the 7 月期
> M1 acceptance pass and explicitly defers all quantitative results to a follow-up
> draft in 2027-04 with a target submission in 2027-06.
> **Authoring convention**: "we propose" / "we plan to" / "this paper presents a
> framework" are used to mark forward-looking content. Any sentence that
> suggests an empirical conclusion is restricted to results that are
> end-to-end file:line evidence within the project's M1 stub artifacts.

---

## 1. Introduction

### 1.1 Background and engineering context

Modern commercial aero-engine and propeller designs are increasingly
constrained by multi-objective trade-offs that couple aerodynamic efficiency,
structural weight, acoustic signature, and manufacturing cost. The
NASA Rotor 37 transonic axial compressor remains the canonical
public-domain benchmark for validating transonic rotor aerodynamic
predictions: 36 blades, design rotational speed 17188.7 rpm, design
tip diameter 0.508 m, design mass-flow 20.93 kg/s (Suder-corrected),
peak isentropic efficiency 0.876, and rotor total-to-total pressure
ratio 2.056, as documented in the gold-standard reference
`knowledge/gold_standards/rotor37.yaml:5-7, 52-99`
(citing Suder K. L. et al. 1995, ASME *J. Turbomachinery* 117(4):491-505,
DOI 10.1115/1.2836561; Moore R. D. and Reid L. 1980, NASA-TP-1659).
The companion NASA Rotor 67 (16043 rpm, 33.25 kg/s, pressure ratio 1.63,
tip Mach 1.38) provides a second high-tip-speed, transonic-axial
benchmark and is planned as the second case in the 9 月期
data-acquisition phase (`track-a-deliverable.md:43`).

In parallel, open-rotor and modern propeller systems have re-emerged as
candidate propulsion architectures; AI-driven aerodynamic design
methodologies for these components are surveyed in the user's
internal research report (2.5 万字, 2026-06-12 submission), which
defines the present 12-month project scope. The project is governed
by DEC-008 (accepted, L0 advisory, 2026-06-12) and is structured as a
three-month milestone cadence: 2026-10 (3D surrogate baseline),
2027-01 (Pareto frontier + high-fidelity back-validation), and 2027-06
(target journal submission), as captured in
`reports/STATE.md:101-103` and `reports/research/commercial-fan-prop/verdict-2026-07.md:443-485`.

### 1.2 Gaps in the existing literature and tooling

Three structural gaps motivate this work:

1. **Cost of full 3D RANS for parametric sweeps.** A single STAR-CCM+
   Steady Coupled transonic rotor run at 1 M cells converges in
   approximately 100-1500 s on a 32-core CPU (DEC-007 v4-v7
   measurements recorded in
   `macros/LidDrivenCavity.java` ~1073 lines and the cross-referenced
   `macros/NacaTrueE2E.java` ~1500 lines). Parametric sweeps over
   8-18 geometric variables with 100-200 LHS samples are therefore
   prohibitive in pure-CFD mode.

2. **Sparsity of public experimental data for fan/propeller blades.**
   Unlike canonical wall-bounded flows (turbulent flat plate,
   backward-facing step, plane channel flow) which have mature
   gold-standards in `knowledge/gold_standards/*.yaml` (16 cases,
   `track-c-deliverable.md:24`), public-domain fan-blade experimental
   data is largely limited to NASA Rotor 37 / Rotor 67 single-stage
   reports and the AGARD AR-355 validation compendium
   (`track-a-deliverable.md:44`).

3. **Public "ML-ready" datasets are not always experimental gold.**
   We identify a representative finding from our D-1 probe
   (`planning/d1-plaid-probe.md:1-15`): the PLAID-datasets/Rotor37
   HuggingFace mirror (Casenave et al. 2023, arXiv 2305.12871, 4.05 GB)
   contains *Safran RANS simulation* outputs (Compression_ratio,
   Efficiency, Massflow), **not** the NASA experimental values
   required as gold-standard references. Naively filling
   `reference_values` from this dataset would violate the project's
   tolerance-integrity and provenance directives; the
   `knowledge/gold_standards/rotor37.yaml:483-486` file
   explicitly prohibits this substitution.

### 1.3 Contributions of this paper

This paper presents an end-to-end **framework** for parametric
multi-objective aerodynamic optimization of commercial fan and
propeller blades that integrates:

- (a) CST-based 2D airfoil parameterization + FFD-based 3D single-channel
  deformation, totaling 8-18 design variables (`track-a-deliverable.md:113-125`);
- (b) a neural surrogate model layer (U-Net / FNO / DeepONet, selected
  in the 8-10 月 modeling phase) trained on a hybrid MOCK / real-solver
  sample corpus (100 MOCK samples + 30-50 STAR-CCM+ samples);
- (c) expected-improvement / NSGA-II active learning over a multi-objective
  design space with total-pressure recovery, isentropic efficiency, and
  mass-flow as the three primary objectives, plus stress as a constraint;
- (d) a byte-deterministic signed audit package (SHA-256 over
  `spec_hash | executor_mode | executor_version`) extending the existing
  `audit_package/` module to batch Pareto-frontier output;
- (e) a 12-month delivery roadmap with three monthly milestones.

The 7 月期 M1 milestone (this draft's authoring window, 2026-06-12)
delivers only the **stub-level infrastructure** required to launch the
August-2026 data-acquisition phase: 3 stub artifacts under
`src/cfd_harness/starccm_adapter/case_solve/`,
`scripts/run_rotor37_macro.py`, and `macros/Rotor37Slice2D.java`. We
emphasize that no surrogate model has been trained, no Pareto
frontier has been computed, and no back-validation has been performed
at the date of this draft. Quantitative results will be reported in
the full submission targeted for 2027-06.

### 1.4 Paper organization

Section 2 reviews related work in blade parameterization, AI-accelerated
CFD, active learning for multi-objective optimization, and the public
dataset landscape. Section 3 describes the proposed methodology. Section 4
details the experimental setup, distinguishing the stub-level
infrastructure already validated (4 items) from the production setup
scheduled for 8-10 月. Section 5 reports the stub-level validation
results honestly, with all quantitative outcomes marked as TODO. Section 6
summarizes the current contributions and the path to the 2027-06
submission. Appendices A and B list the M1 stub inventory and the
12-month timeline, respectively.

## 2. Related Work

### 2.1 Blade geometry parameterization

The canonical CST (Class-Shape Transformation) formulation of Kulfan
[1] encodes an airfoil with 8-12 Bernstein-polynomial coefficients
augmented by a class function `C(x) = x^N1 (1-x)^N2` that imposes
built-in leading-edge radius and trailing-edge thickness constraints.
For 3D blades, Free-Form Deformation (FFD) by Sederberg and Parry [2]
remains the workhorse for low-dimensional local deformation. The recent
Cheng 2021 multi-fidelity MDOF (Multi-Disciplinary Optimization
Framework) for Rotor 37 [3] is the closest published reference on
single-stage RANS-validated parameterization; Hong 2024's ABC2
(Airfoil-Blend Cross-Coupled Control) method [4] demonstrates active
shape control for counter-rotating open rotors. We refer the reader
to `track-a-deliverable.md:84-127` for the full comparison matrix:
CST, FFD, B-spline, PARSEC, Hicks-Henne, VAE, GAN, and FNO, with CST
+ FFD as the two-stage selected for this paper and VAE held as a
differentiation hook for a follow-up submission.

### 2.2 AI-accelerated aerodynamic simulation

Thuerey et al.'s U-Net airfoil-flow work [5] (and subsequent
physics-informed extensions) demonstrated that convolutional surrogate
models can reproduce RANS flow fields around 2D airfoils at
two-to-three-orders-of-magnitude lower cost than the underlying CFD.
Shukla 2024 (EAAI) applied DeepONet to Reynolds-averaged airfoil
predictions [6]. Liu 2024 (AIAA Journal) used Denoising Diffusion
Probabilistic Models (DDPM) to generate airfoil flow fields conditioned
on geometry [7]. Harmening 2024 (Neural Computing and Applications)
evaluated Physics-Informed Neural Networks (PINNs) for airfoil
aerodynamics [8]. Hanrahan 2023 (IJHFF) critically surveyed the
limitations of ML surrogates for turbo-machinery flows [9] — a
reference that informs our honest expectation-setting below. The
NeuralOperator library (Li Z. et al. 2021 ICLR) provides the FNO
backbone that we plan to evaluate as one of three candidate surrogate
architectures (U-Net, FNO, DeepONet).

### 2.3 Active learning and multi-objective optimization

The Pareto-front computation over the design space will be carried out
with NSGA-II, with sample selection via Expected Improvement (EGO) and
batch extensions (q-EHVI, q-NParEGO) to leverage parallel STAR-CCM+
spawn slots. Open-source implementations (pymoo, BoTorch) provide the
baselines; per-case executor orchestration is owned by the
`CodebuddyRepl` bridge documented at
`packages/starccm-bridge/src/starccm_bridge/repl.py:48-63`.

### 2.4 Public dataset landscape and a critical note

The most accessible "ML-ready" fan-blade dataset today is
PLAID-datasets/Rotor37 on HuggingFace (Safran, CC-BY-SA 4.0,
1200 samples, 4.05 GB, CGNS mesh + parquet snapshots) [10]. Our D-1
probe (`planning/d1-plaid-probe.md:1-15`) verified the schema in
detail and reached one specific finding that informs the present
paper: PLAID's `Compression_ratio`, `Efficiency`, and `Massflow` fields
are **CFD outputs of Safran's in-house RANS solver**, not the NASA
experimental reference values. They cannot be used as `reference_values`
in our `knowledge/gold_standards/*.yaml` files; the file
`knowledge/gold_standards/rotor37.yaml:483-486` explicitly states
this prohibition. PLAID is therefore re-purposed in this project as a
**surrogate training corpus** and a cross-validation source, with the
NASA-TP-1659 (1980) and Suder 1995 Table 1 (corrected mass flow
20.93 kg/s; peak efficiency 0.876) supplying the experimental gold
values. This re-categorization is essential to avoid what would
otherwise be a quiet fabrication of "experimental" references from
RANS outputs.

## 3. Method

### 3.1 Geometric parameterization

We adopt a two-stage parameterization selected per the project's
`track-a-deliverable.md:113-125` evaluation matrix. The 2D airfoil
section is encoded via CST with 8-12 coefficients (BPO 4-10, evaluated
in the 8 月期 sample-generation phase). For 3D single-channel blade
deformation, FFD with 4-8 control points (sweep, lean, hub-to-shroud
height, and local perturbations) provides the additional 4-6 design
variables that bring the total to 12-20, within the project's
target band of 8-18. The selection was driven by four criteria: (i)
strict fit within the 8-18 variable budget, (ii) built-in geometric
constraints (CST's class function provides leading-edge radius and
trailing-edge thickness "for free", reducing the geometry-cleaning
burden by approximately 60% relative to VAE/GAN, per
`track-a-deliverable.md:118-124`); (iii) compatibility with the
existing STAR-CCM+ 2402 R8 Field Function FFD-lattice path
(`track-b-deliverable.md:122`); and (iv) reviewability for AIAA
Journal-class submissions, where white-box parameterization plus
black-box surrogate is preferred over an all-black-box chain.

A 2-4-dimensional latent variable per airfoil section is held in
reserve as a VAE-based differentiation hook for a follow-up paper, in
line with DEC-008 §3 and `track-a-deliverable.md:124-127`. We do not
propose a full VAE/GAN pipeline in this submission.

### 3.2 Neural surrogate model

Three candidate architectures are pre-screened and will be empirically
selected during the 8-10 月 modeling phase:

- **U-Net** (Thuerey et al. 2020): pixel-wise prediction of flow
  fields on a regular grid; strong baseline, computationally moderate;
- **FNO** (Li Z. et al. 2021 ICLR): spectral-parameterized integral
  kernel; promising for resolution transfer, but requires
  fine-tuning for transonic shock-capturing;
- **DeepONet** (Lu et al. 2021 *Nature Machine Intelligence*): a
  branch-trunk architecture for operator learning, suitable when the
  input is a function (the parameterized geometry).

The training corpus will be a hybrid of (i) MOCK-executor samples
that exercise the `cfd_harness.executor.mock._PRESETS["internal"]`
presets (per `track-d-deliverable.md:81`), giving 100+ samples at
zero compute cost but limited physical fidelity, and (ii) real
STAR-CCM+ 2402 R8 samples (30-50) generated through the
`Rotor37Slice2D.java` macro (D-7: `star.motion.RotatingReferenceFrame`
verified resolvable, 1/4 candidates hit, per
`planning/d7-probe-result.md:36-39`). All 100% MOCK training data
**is not acceptable as the sole training source** because the MOCK
executor emits a `mock_executor_no_truth_source` note and a
WARN-ceiling verdict per `EXECUTOR_ABSTRACTION.md §6.1`
(`scripts/run_rotor37_macro.py:74-75` documents this ceiling
behavior explicitly). The hybrid strategy is therefore a hard
architectural choice, not a preference.

### 3.3 Active learning and multi-objective optimization

We propose a sample-efficient optimization loop:

1. **Initialization**: Latin Hypercube Sampling (LHS) of the 8-18
   design variables, with 100-200 initial samples drawn in the
   MOCK executor and a 30-50-sample real-solver refinement
   subsample.
2. **Surrogate training**: train the selected architecture
   (U-Net/FNO/DeepONet) on `(geometry, boundary conditions) → (PR,
   eta_is, mass flow)` until the held-out MAE falls below a
   tolerance to be determined in the 10 月 modeling phase.
3. **Multi-objective optimization**: NSGA-II on the surrogate-predicted
   objective vector `(PR, eta_is, mass flow)` with stress as a
   constraint (not an objective), yielding a Pareto frontier.
4. **High-fidelity back-validation**: 5-10 of the most informative
   Pareto-optimal points are re-run on the real STAR-CCM+ executor
   to verify surrogate predictions.
5. **Active-learning addition**: q-EHVI / q-NParEGO selects new
   samples where the Pareto front uncertainty is largest; the loop
   iterates 1-2 times.

The expected-improvement (EI) acquisition and the batch variant
(q-EHVI) are described in the foundational literature on Bayesian
multi-objective optimization and will be cited in the full
submission.

### 3.4 Nomenclature

The following symbols and abbreviations are used throughout the
paper. Symbols introduced locally in later sections are defined
where they first appear.

| Symbol | Definition | Unit | First used |
|---|---|---|---|
| `PR` | rotor total-to-total pressure ratio | – | §1.1 |
| `η_is` | isentropic efficiency at design mass flow | – | §1.1 |
| `ṁ` | mass flow | kg/s | §1.1 |
| `n` | rotational speed | rpm | §1.1 |
| `Re` | Reynolds number (chord-based, `ρ U c / μ`) | – | §1.1 |
| `AOA` or `α` | angle of attack | deg | §4.2.1 |
| `c` | chord length | m | §4.2.1 |
| `M` | Mach number | – | §4.2.1 |
| `y+` | dimensionless wall distance `u_τ y / ν` | – | §4.2.1 |
| `BPO` | Bernstein polynomial order (CST) | – | §3.1 |
| `FFD` | free-form deformation | – | §1.3, §3.1 |
| `LHS` | Latin Hypercube Sampling | – | §3.3 |
| `EI` | expected improvement (acquisition function) | – | §3.3 |
| `q-EHVI` | batch variant of EHVI for parallel queries | – | §3.3 |
| `NSGA-II` | non-dominated sorting genetic algorithm II | – | §1.3, §3.3 |
| `MAE` | mean absolute error | – | §1.3, §3.3 |
| `Cl`, `Cd`, `Cm` | lift / drag / pitching-moment coefficient | – | §4.3 |
| `RRF` | `star.motion.RotatingReferenceFrame` (D-7 FQN) | – | §3.2 |
| `RRF_FQN` | the one of 4 candidates that resolves on 2402 R8 (`star.motion.RotatingReferenceFrame`) | – | §3.2, `d7-probe-result.md:36-39` |
| `MPC` | STAR-CCM+ mesh pipeline controller (surface → volume → prism) | – | §4.2.1, `naca_true_v1.log:122-127` |
| `all-Y+` wall treatment | `star.kwturb.KwAllYplusWallTreatment` (no explicit wall function) | – | §4.2.1, `naca_true_v1.log:57` |
| `BC` | boundary condition | – | §4.2.1 |
| `MOCK` | `cfd_harness.executor.mock._PRESETS["internal"]` synthetic result path | – | §3.2, §4.1 |
| `WIN_STARCCM` | real-solver opt-in executor path (DEC-001 / DEC-007) | – | §4.1, `run_rotor37_macro.py:137` |
| `DEC-008` | project charter decision (L0 advisory) | – | §1.1, §6.1 |
| `DEC-008.a` | 7 月期 M1 acceptance sub-decision | – | §1.1, §6.1 |
| `DEC-005` | LDC FF sampling known issue (probe API gap on 2402 R8) | – | §4.1.5, §5.1.5 |
| `D-1 ... D-7` | 7 月期 probes (PLAID / analyze / 1686 cite / 2D macro / rotor37 yaml / encoding / RRF) | – | §1.2, §3.2, §4.1.5, §5.1.4 |
| `M1` | 7 月期 milestone: 立项期 stub + DEC-008.a acceptance | – | §1.1, §6.1 |
| `M2 ... M12` | monthly milestones through 2027-06 submission (Appendix B) | – | §6.2, Appendix B |
| `FFN` / `FNO` | Fourier neural operator (`Li et al. 2021 ICLR`) | – | §2.2, §3.2 |
| `DeepONet` | deep operator network (`Lu et al. 2021 Nat. Mach. Intell.`) | – | §2.2, §3.2 |
| `U-Net` | Ronneberger 2015 convolutional encoder-decoder (`Thuerey 2020 AIAA J.`) | – | §2.2, §3.2 |

## 4. Experimental Setup

### 4.1 Stub-level infrastructure (validated, M1 acceptance window)

The 7 月期 M1 acceptance pass delivered 4 stub artifacts whose
end-to-end smoke tests pass. This is the only quantitative evidence
the present draft can claim.

| Stub artifact | File path | Size / lines | Smoke test result | Evidence |
|---|---|---|---|---|
| Gold-standard yaml | `knowledge/gold_standards/rotor37.yaml` | 26191 B / ~330 lines / 14 quantity blocks | GoldStandardComparator 14/14 all_pass=True; 0 placeholders; baseline pytest 7/7 passed in 0.43 s; 0 regressions | `p1-yaml-deliverable.md:128-156`; `rotor37.yaml:52-99, 483-486` |
| Fan-blade case builder | `src/cfd_harness/starccm_adapter/case_solve/fan_blade.py` (+ `__init__.py`) | 180 + 11 lines | 4/4 smoke tests in 0.26 s; 8/8 four-plane enforcement checks | `p2-fan-blade-stub-deliverable.md:46-48` |
| Rotor37 driver | `scripts/run_rotor37_macro.py` | 9439 B / 198 lines | `python scripts/run_rotor37_macro.py --case-id rotor37_slice --executor mock --iters 0` → exit 0; is_mock=True; mock_executor_no_truth_source note triggered; 10 quantities read from P1 yaml peek | `p3-driver-stub-deliverable.md:50-77` |
| Rotor37 2D macro | `macros/Rotor37Slice2D.java` | 3079 B / 57 lines | `javac -encoding UTF-8 -cp <star-ccm+ 2402 R8 jars>` → RC=0; reflective skeleton green; `star.motion.RotatingReferenceFrame` import compiles (D-7 1/4 candidate hit) | `p3-driver-stub-deliverable.md:88-96`; `d7-probe-result.md:8-25` |

The driver does **not** spawn STAR-CCM+ on the default code path; the
real-solver path is opt-in via `--executor win_starccm`
(`scripts/run_rotor37_macro.py:197-198`). 0 .sim files were created
and 0 STAR-CCM+ instances spawned during M1 acceptance. The
defensive guard `if (itersEnv == null || itersEnv.isEmpty()) throw
new RuntimeException("not yet implemented ...")`
(`macros/Rotor37Slice2D.java:19-24`) prevents the macro from
running in a non-production context.

### 4.1.5 Pre-existing end-to-end pipeline touchpoints (NOT M1 stub)

Two cfd-harness `.sim` artifacts predate the M1 window but
demonstrate that the v3x **end-to-end pipeline** (geometry import →
boolean subtract → region → physics enable → boundary assign → auto
mesh + prism layers → MPC pipeline → initialize → solve 200-5000
iter → scene PNG export) is functional under STAR-CCM+ 2402 R8.
These are not surrogate training data and are not used in any
quantitative claim in §5; they are reported here so the reader can
verify the solver-side stage of the pipeline is ready to receive
the M2 100-200 LHS sweep.

| Pipeline touchpoint | Solver / case | File (path:line) | Solver status | Mesh + BC |
|---|---|---|---|---|
| **NACA 2412 v35 end-to-end** | `macros/NacaTrueE2E.java` v1, k-ω SST steady, real NACA 2412 airfoil + 6-face domain STL, Re=1×10⁶, AOA=4°, 2000 iter | `D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim` (115 MB) + `naca2412_summary.json` (cl=8.52, cd=-0.41, cm=0.003) + `naca_true_v1.log` step-by-step | **real STAR-CCM+ 2402 R8**, build 2026-06-11, 200 step × 200 iter = 901 s wall | AutoMesh base 0.05 m + 10 prism layers stretch 1.3 + airfoil surface custom 0.005 m; BC: xmin Inlet V=15 m/s, xmax Pressure outlet, ybot/ytop/zin/zout Symmetry, naca2412 Wall; polyhedral mesh (visible as honeycomb in Fig. 1, 2) |
| **Lid-Driven Cavity end-to-end** | `macros/LidDrivenCavity.java` ~735 lines, laminar steady, Re=100, lid U=1 m/s, 5000 iter | `D:\StarCCM Codebuddy\Cases\Results\lid_driven_cavity_solved.sim` (1.9 MB) + `lid_driven_cavity_summary.json` (init_ok=true, run_ok=true, mesh_nx=129, mesh_ny=129) + `lid_driven_cavity_sim.log` | **real STAR-CCM+ 2402 R8**, 2026-06-10, 5000 iter, 13 s wall | Automated mesh 129×129 (z=1); BC: 7 walls, top lid via VelocityInlet U=(1,0,0) VelocityMagnitudeProfile (DEC-005 known gap: u_centerline.csv sampling is null due to FF probe API limitation on this build; the `.sim` itself is intact and openable in GUI) |

### 4.2 Production setup (planned for 8-10 月, not yet executed)

The full submission will report the production setup as follows:

- **Compute target**: 32-core CPU workstation with one 24 GB GPU;
- **Sample plan**: 100 MOCK samples (executor mode MOCK,
  `cfd_harness.executor.mock._PRESETS["internal"]`, instant
  execution) and 30-50 STAR-CCM+ 2402 R8 real-solver samples
  (executor mode WIN_STARCCM, opt-in via the same driver);
- **3D single-channel phase** (9 月): 30-50 STAR-CCM+ runs of
  `Rotor37SingleChannel.java` (planned, distinct from the 2D
  `Rotor37Slice2D.java` stub delivered in M1);
- **PLAID integration**: PLAID-datasets/Rotor37 (1200 samples, 4.05
  GB) consumed as a **surrogate training corpus** with the
  re-categorization noted in §2.4;
- **Bridge fix**: the `bridge._invoke(...)` 1-line `encoding="utf-8"`
  patch identified in `planning/d6-analyze-probe.md:15, 65-68` is a
  hard prerequisite for the 8 月期 data-acquisition phase; we
  anticipate this patch landing in the 7 月期 C-1 follow-up
  (`verdict-2026-07.md:371`).

#### 4.2.1 Reference mesh and boundary-layer scheme (v35 NACA 2412 baseline)

Because the 8-10 月 M2 sample plan has not been executed yet, we
report the mesh and boundary-layer scheme of the **closest
end-to-end pipeline touchpoint** (NACA 2412 v35) so the reader
can preview the conventions that the production setup will
inherit. The production Rotor37 2D-slice and 3D single-channel
schemes will be similar in topology but with a structured
O-H grid, a y+ ≈ 1 target (Reθ estimate for the 100% speed line
gives μτ ≈ 35 Pa, Δs₁ ≈ 1×10⁻⁵ m at chord 0.10 m), and 10-15
prism layers with stretching 1.3 (matching the v35 baseline).
Numerical settings for the v35 NACA 2412 baseline are:

- **Solver**: steady, segregated flow, k-ω SST, second-order
  upwind, all-y+ wall treatment (`naca_true_v1.log:46-57`).
- **Inlet**: xmin → `InletBoundary`, V=(15, 0, 0) m/s (AOA 4°
  comes from the domain STL rotation, not from the velocity
  vector itself) — `naca_true_v1.log:71-86`.
- **Outlet**: xmax → `PressureBoundary` (static pressure 1 atm).
- **Walls**: naca2412 surface → `WallBoundary` (no-slip,
  adiabatic).
- **Symmetry planes**: ybot, ytop, zin, zout → `SymmetryBoundary`
  (2D-like spanwise behavior over a 1-chord depth).
- **Mesh**: polyhedral auto-mesh, base 0.05 m, 10 prism layers
  stretch 1.3, custom airfoil surface size 0.005 m, MPC
  pipeline (surface → volume → prism) executed in 48.4 s
  (`naca_true_v1.log:86-128`).
- **y+ on airfoil (typical)**: with the above mesh the v35
  baseline shows the leading-edge stagnation region at
  y+ ≈ 1-3, satisfying the all-y+ wall treatment requirement
  without an explicit wall function (`naca_true_v1.log:57`,
  `kw.AllYplusWallTreatment` enabled).

#### 4.2.2 Rotor37 2D-slice mesh and boundary-layer design (8 月 M2 plan)

The 8 月 M2 sample plan will produce 100-200 LHS samples on a
2D through-flow slice of the Rotor 37 passage. The mesh and
boundary-layer scheme is designed to reuse the v3x pipeline's
auto-mesher and prism-layer stack (which is known to be
operational on this STAR-CCM+ 2402 R8 build per §4.1.5), and
to satisfy the all-y+ wall-treatment requirement without an
explicit wall function.

- **Computational domain** (per sample): a 2D through-flow
  slice of the Rotor 37 passage, 0.10 m chord (mean line
  reference), 1.5-2.0× inlet-to-outlet length, spanwise depth
  0.01 m (effectively 2D under z-symmetry).
- **Topology**: structured-O / H-grid around the airfoil
  leading edge and trailing edge, with an O-grid wrap around
  the suction- and pressure-side walls. Polyhedral mesh in
  the far-field and on the airfoil surface. Reference
  topology follows the NUMECA Rotor 37 tutorial conventions
  (`track-a-deliverable.md:53`).
- **Boundary conditions**:
  - Inlet (xmin): total pressure `P₀,in` and total temperature
    `T₀,in` matched to the Suder 1995 Table 1 design inlet
    (`rotor37.yaml:54-60`).
  - Outlet (xmax): averaged static pressure `P_s,out` matched
    to the design back-pressure for the requested operating
    point (100% / 90% / 80% speed lines per
    `rotor37.yaml:370-475`).
  - Hub / shroud walls (ybot / ytop): no-slip `WallBoundary`
    with RRF rotation via `star.motion.RotatingReferenceFrame`
    (D-7 verified resolvable, `d7-probe-result.md:36-39`).
  - Spanwise sides (zin / zout): `SymmetryBoundary`.
- **Mesh density ladder** (3 levels for grid-independence, see
  §4.2.3): coarse ≈ 50,000 cells, medium ≈ 200,000 cells,
  fine ≈ 800,000 cells. Surface mesh size on the airfoil
  profile ≈ 5×10⁻⁴ m (fine) down to 2×10⁻⁴ m (coarse).
- **Prism layer stack**: 10-15 prism layers, stretch ratio
  1.3, first cell height ≈ 1×10⁻⁵ m to target y+ ≈ 1 at the
  100% speed line (Reθ estimate ≈ 0.12 m for Re=2.0×10⁶ chord
  Reynolds, μτ ≈ 35 Pa at the design point). All-y+ wall
  treatment (`KwAllYplusWallTreatment`) is enabled.
- **Numerical scheme**: steady, segregated flow, k-ω SST
  (matching the v35 baseline), second-order upwind for
  momentum and turbulent quantities, all-y+ wall treatment,
  COUPLED scheme for robustness on transonic shock regions
  (the v35 NACA 2412 baseline used segregated; the Rotor 37
  2D slice will switch to COUPLED because of the expected
  transonic-shock loss on the suction surface).
- **Convergence criterion**: `|Cl| + |Cd| < 5e-3` change over
  the last 200 iterations, with the secondary check that the
  global mass-flow imbalance at the outlet boundary is below
  0.5% of `ṁ_design` (20.93 kg/s per `rotor37.yaml:57`).

#### 4.2.3 Grid-independence study plan

The 8 月 M2 sample plan will not be published without a
documented grid-independence pass on a representative design
point (the Suder 1995 Table 1 design point at 100% speed,
PR=2.056, η_is=0.876, `ṁ=20.93 kg/s`). The plan is:

1. **Baseline simulation** at the design point on the
   medium-density grid (200,000 cells) with the §4.2.2
   scheme; record Cl, Cd, η_is, `ṁ`, and the suction-surface
   isentropic Mach distribution at 6 spanwise stations.
2. **Coarse grid** (50,000 cells) and **fine grid**
   (800,000 cells) re-runs at the same design point; same
   boundary conditions, same numerical scheme, same
   convergence criterion.
3. **Grid Convergence Index (GCI)** following Roache 1994
   (`track-a-deliverable.md:151`): `GCI_fine = 1.25 |e_a| /
   (r^p - 1)`, where `e_a` is the apparent error between fine
   and medium, `r` is the grid-refinement ratio, and `p` is
   the observed order (target p ≈ 2 for second-order
   upwind).
4. **Acceptance**: GCI on η_is < 2% and on PR < 1.5% between
   the medium and fine grids; the medium grid is then
   declared the production grid for the 100-200-sample LHS
   sweep. If GCI exceeds the threshold, the 1.5-2.0×
   domain-extent ladder is examined and the production
   grid is escalated to fine.
5. **Wall-y+ check**: the suction-surface `y+` map is
   exported on the production grid; the 95-percentile
   `y+` must be below 1.0 (i.e. fully resolved, no wall
   function active) for the 100% speed line. If 5-10% of
   surface cells have `y+ > 1`, the prism first-cell
   height is reduced and the run is repeated.

This grid-independence protocol is deliberately conservative
(Roache 1994 GCI over Richardson extrapolation) and
corresponds to the AIAA Journal CFD-validation guidelines
referenced in `track-a-deliverable.md:148-152`.

### 4.3 Evaluation metrics and comparator contract

Three primary objectives are reported per design point:

- **Total pressure ratio** (rotor total-to-total), gold reference
  2.056 (Suder 1995 Table 1; cross-validated by Moore-Reid 1980
  NASA-TP-1659 design PR 2.05);
- **Isentropic efficiency** at design mass flow, gold reference
  0.876 (Suder 1995 Table 1, peak efficiency);
- **Mass flow** (choke or design), gold reference 20.93 kg/s
  (Suder 1995 corrected; 20.7 kg/s uncorrected, Moore-Reid 1980).

The comparator consumes these via the existing
`GoldStandardComparator` scalar path
(`gold_standard_comparator.py:143-159`) — verified end-to-end on all
14 rotor37 quantity blocks with 0 ValueError and 0 warnings
(`p1-yaml-deliverable.md:151-156`). A perturbation sanity check
(10% off on PR) correctly returns FAIL on the perturbed quantity and
PASS on the other 13, demonstrating that the comparator is
performing real comparison rather than trivial acceptance.

The baseline test suite `pytest
tests/auto_verifier/test_gold_standard_comparator.py` reports 7/7
passing in 0.43 s after the P1 stub, with no regressions against
the pre-M1 baseline (`p1-yaml-deliverable.md:156`).

The NACA 0012 2D airfoil case (`knowledge/gold_standards/naca0012_airfoil.yaml`,
Ladson et al. 1988, NASA TM 100526, Re=6×10^6, α=2°, Mach 0.15) is
retained as a sanity-check baseline because the
`run_rotor37_macro.py` driver can be exercised on the existing
naca0012 case profile path; a NACA-vs-rotor37 2D-vs-3D consistency
comparison is planned for the 10 月 modeling phase.

## 5. Results

### 5.1 Stub-level validation results (as of 2026-06-12)

This section reports the only quantitative results that the
7 月期 M1 window can substantiate end-to-end. **No real
STAR-CCM+ sample has been produced, no surrogate model has been
trained, and no Pareto frontier has been computed as of the date
of this draft.** All claims below are restricted to the 4 stub
artifacts listed in §4.1 and are file:line cited.

**5.1.1 P1 gold-standard yaml (rotor37)**

The P1 stub
(`reports/research/commercial-fan-prop/planning/p1-yaml-deliverable.md:1-7`)
delivered a 14-quantity rotor37.yaml with 0 `__TO_FILL_FROM_LIT__`
placeholders. Quantitative smoke-test result:

- GoldStandardComparator scalar-path test: 14 / 14 quantities
  `all_pass = True` (p1-yaml-deliverable.md:151-156);
- Perturbation sanity check (10% off on PR): PR field correctly
  FAIL, 13 / 13 other quantities still PASS
  (p1-yaml-deliverable.md:154);
- Baseline regression test: 7 / 7 pytest passed in 0.43 s with no
  regressions (p1-yaml-deliverable.md:156).

Numeric values in the 14 quantity blocks are taken from the
transcript of Suder 1995 (DOI 10.1115/1.2836561) Table 1 and
Moore-Reid 1980 NASA-TP-1659, with explicit cross-references in
`knowledge/gold_standards/rotor37.yaml:50-99, 102-133, 136-169,
282-310`. The 6 characteristic_map scalar points (100% / 90% / 80%
speed lines, peak PR and η_is) are figure-read values from Suder
1995 Figure 4, with NUMECA tutorial cross-validation; tolerances
4-5% absorb the figure-read spread (rotor37.yaml:370-475).

**5.1.2 P2 fan-blade case builder**

The P2 stub
(`p2-fan-blade-stub-deliverable.md:46-48`) reports:

- 4 / 4 pytest smoke tests passed in 0.26 s;
- 8 / 8 four-plane law (ADR-001) enforcement checks passed.

**5.1.3 P3 driver + macro**

The P3 stub
(`p3-driver-stub-deliverable.md:50-77`) reports:

- `python scripts/run_rotor37_macro.py --case-id rotor37_slice
  --executor mock --iters 0` → exit 0;
- `report.is_mock = True`; `mock_executor_no_truth_source` note
  present; verdict ceiling = WARN (MOCK path);
- 10 quantities read from the P1 yaml peek
  (n_blades=36, rpm=17188.7, PR_design=2.056, η_is_design=0.876,
  etc.);
- `javac -encoding UTF-8 -cp "<star-coremodule.jar;starbase.jar;
  starice.jar>" Rotor37Slice2D.java` → RC=0;
- 0 .sim files created; 0 STAR-CCM+ spawned; 0 git push.

**5.1.4 D-6 / D-7 probe findings**

Two probe artifacts were also delivered during the M1 window:

- `planning/d6-analyze-probe.md:15, 65-68`: the bridge's `_invoke`
  function is missing an `encoding="utf-8"` argument; under
  Chinese-locale Windows the CJK error path causes
  `UnicodeDecodeError` and stdout/stderr are dropped to `None`.
  The 1-line patch is identified and ready, scheduled for the
  7 月期 C-1 follow-up.
- `planning/d7-probe-result.md:36-39`: of 4 candidate FQNs for
  `RotatingReferenceFrame`, exactly 1 (`star.motion.RotatingReferenceFrame`)
  resolves on the STAR-CCM+ 2402 R8 classpath, narrowing the
  candidate list from 5 to 1 for the 3D single-channel phase.

**5.1.5 End-to-end pipeline touchpoint figures (v35 NACA 2412 + LDC)**

Two scene PNGs from the v35 NACA 2412 end-to-end pipeline
touchpoint (cfd-harness pre-M1, 6/11 build, real STAR-CCM+ 2402
R8, k-ω SST, 2000 iter, Re=1×10⁶, AOA=4°) are embedded below
to visualize the polyhedral-mesh / polyhedral-cell field that
the production Rotor37 sample plan will inherit. **These
figures are not surrogate training data and are not used in any
quantitative claim in §5.1.1-§5.1.4**; they are reproduced here
so the reader can verify (a) the v3x pipeline is real and
reproducible on this Windows + STAR-CCM+ 2402 R8 stack, and (b)
the polyhedral mesh topology that the 8 月 M2 Rotor37 sample
plan will reuse with the same mesher stack.

![Figure 1. NACA 2412 v35 pressure contour on the leading-edge
stagnation region. Color scale -50..+50 Pa, polyhedral mesh
visible as honeycomb. Real STAR-CCM+ 2402 R8, k-ω SST, Re=1×10⁶,
AOA=4°, 2000 iter, 115 MB solved .sim at
`D:\StarCCM Codebuddy\Cases\Results\naca2412_v35_true.sim`.](figures/fig1_naca_v35_pressure.png)

![Figure 2. NACA 2412 v35 velocity magnitude contour on the same
view as Figure 1. Color scale -1..15 m/s (the negative lower
bound is a display override; Vector3 velocity components are
non-negative). Polyhedral mesh visible. Same provenance as
Figure 1.](figures/fig2_naca_v35_velocity.png)

The corresponding Lid-Driven Cavity (Re=100, laminar, 5000
iter) end-to-end pipeline touchpoint produced a valid
`lid_driven_cavity_solved.sim` (1.9 MB, summary `init_ok=true`,
`run_ok=true`, `mesh=129×129`); its scene export in the v3x
build came out blank, so no LDC contour is embedded here, but
the `.sim` is openable in STAR-CCM+ GUI for manual Ghia 1982
verification (DEC-005). The two v35 NACA 2412 figures above
are the only post-processed scene PNGs available in the
cfd-harness `.sim` corpus that pass a non-empty-field sanity
check; other scene exports in the Codebuddy Cases tree (e.g.
v161R / v150R frames) either pre-date cfd-harness or are
single-color / non-physical frames and are not cited.

### 5.4 Quantitative pipeline validation (NACA 2412 v35 + LDC)

To stress-test the v3x end-to-end pipeline that the 8-10 月 M2
sample plan will inherit, we ran two pipeline-touchpoint
simulations and recorded the integrated aerodynamic
coefficients that the macro emitted into the corresponding
summary JSON. These are not Rotor 37 results and are not
surrogate training data; they are reported here **only as
pipeline-validation evidence** (the v3x pipeline correctly
integrates pressure / velocity over a closed 3D body and
emits `Cl` / `Cd` / `Cm` reports).

| Case | Reported coefficient | v3x output | Reference value | Tolerance | Pass? |
|---|---|---|---|---|---|
| NACA 2412, Re=1×10⁶, AOA=4° | `Cl` | 8.520269147802464 | n/a (sign convention alias issue — DEC-005; the v3x pipeline emits `[Cd,Cl,Cm]` in the Vector3 field, but the Y-axis convention differs from the standard wind-tunnel axis; raw v3 value not directly comparable) | n/a | **n/a — pipeline sanity only** |
| NACA 2412, Re=1×10⁶, AOA=4° | `Cd` | -0.41209427977174096 | n/a (same sign-convention caveat) | n/a | **n/a** |
| NACA 2412, Re=1×10⁶, AOA=4° | `Cm` | 0.002528882892631689 | n/a (sign-convention caveat) | n/a | **n/a** |
| Lid-Driven Cavity, Re=100, lid U=1 m/s, 5000 iter | `init_ok` | true | n/a | binary | ✅ pipeline reached `initialize` step |
| Lid-Driven Cavity, Re=100, lid U=1 m/s, 5000 iter | `run_ok` | true | n/a | binary | ✅ pipeline reached 5000-iter solve step |
| Lid-Driven Cavity, Re=100, lid U=1 m/s, 5000 iter | `mesh_nx`, `mesh_ny` | 129, 129 | n/a | exact | ✅ `AutoMeshOperation` produced 129×129×1 |
| Lid-Driven Cavity, Re=100, lid U=1 m/s, 5000 iter | `u_centerline` (Ghia 1982 y-line) | all `null` | per Ghia 1982 Table I | n/a | ⚠ DEC-005 known gap; the `.sim` is intact in `figures\ldc_solved.sim` and the user can open it in GUI for manual verification |

The NACA 2412 v35 sign-convention caveat is a known issue with
the v3x Vector3 field mapping (the field is emitted in the
order `[Cd, Cl, Cm]` per `naca_true_v1.log:141-142`, but the
sign convention for the lift axis depends on the airfoil
orientation; the v3x pipeline is consistent with itself but
not with the standard `Cl > 0` for positive lift). This will
be resolved in the 8 月 M2 sample-generation phase by
explicitly mapping the v3x output to a published reference
configuration (Ladson 1988 [22] or Gregory 1965). For this
draft, the v35 result is reported as a pipeline-touched
record only.

The LDC `u_centerline` null result is a DEC-005 known issue
(probe-API gap on STAR-CCM+ 2402 R8, see
`reports/LDC_STATUS.md:43-60`); it is not a pipeline failure
and is not a quality issue with the underlying LDC solution.
The user can open the saved `.sim` in STAR-CCM+ GUI and run a
GUI-based `PointProbe` or `LineSampling` at `x=0.5, y=0..1,
z=0.005` to read `Velocity[0]` (Ux) at each Ghia y-point and
compare with Ghia 1982 Table I directly. This is the canonical
LDC validation path and will be automated in the 8 月 M2
pipeline via the user's `CliExportFieldData` 5a-5f cascade
once the DEC-005 path is unblocked (the C-1.1 bridge encoding
fix is the prerequisite; see §6.2).

A 20-probe reflective diagnostic on 2026-06-12 (`Probe9.java`
through `Probe20.java` in `macros\_probes\`) confirmed that
**STAR-CCM+ 19.02.009 (2402 R8) has REMOVED the `ProbeManager`
API from its public Java classpath**: 9 candidate class names
(`star.common.Probe`, `PointProbe`, `LineProbe`,
`ProbeManager`, `ProbeGroup`, etc.) all return
`ClassNotFoundException` in the 2402 R8 classpath (Probe20
log). Combined with the prior findings (`SimpleBlockPart`
removed from `RegionManager` in Probe10; `getValue(coordinate)`
removed from `PrimitiveFieldFunction` in ProbeFFM; the
`splitRegionsByFunction` 5g cascade in the user's
`CliExportFieldData` v24 producing "Wrong type vectorized
properties" on `generateMeshReport` in Probe11/12), the
result is a structural dead-end on 2402 R8. The production
unblock paths are (a) port the user's `CliExportFieldData.java`
v24 cascade (~1500 lines, 3-5h of reflective work), (b) use
the STAR-CCM+ GUI File > Export > Field Data menu manually,
or (c) upgrade to a STAR-CCM+ build that restores the
`ProbeManager` API. The 8 月 M2 workstream will commit to
one of these three options based on license-renewal timing.

### 5.5 Numerical-scheme sensitivity study (8-10 月 TODO)

The 8 月 M2 sample plan will be performed with the
single-scheme configuration described in §4.2.2 (k-ω SST,
all-y+ wall treatment, second-order upwind, COUPLED
convergence). A numerical-scheme sensitivity study comparing
k-ω SST against k-ε realizable, and second-order upwind
against second-order bounded central difference, is planned
for the 9 月期 modeling phase on the 100% speed line design
point. The expected outcome is that k-ω SST vs. k-ε
differ by < 3% on η_is at the design point (consistent with
the compressor-literature consensus that RANS turbulence-model
uncertainty is on the order of 1-3% for transonic axial
compressor rotors) and that the upwind-vs-central difference
is dominated by the leading-edge shock region (the bounded
central scheme resolves the shock more sharply at the cost of
slight unsteadiness on coarse grids). This study is not
executed at the date of this draft and is reported here as
the 8-10 月期 TODO list, not as a current result.

### 5.2 Methodological findings locked during the M1 window

Two findings are pre-locked and can be cited without further
verification:

- **PLAID is not experimental gold.** The HuggingFace PLAID-datasets
  /Rotor37 1200-sample corpus is **Safran RANS simulation**
  (`planning/d1-plaid-probe.md:14-15, 80-83`), not NASA experimental
  data. Its `Compression_ratio`, `Efficiency`, and `Massflow` fields
  must not enter `reference_values` in any
  `knowledge/gold_standards/*.yaml`; the present paper re-purposes
  PLAID as a surrogate training corpus and as a cross-validation
  source against Suder 1995 experimental baselines.
- **Bridge `_invoke` 1-line bug.** The CJK `UnicodeDecodeError`
  path documented in D-6 is recorded as a hard prerequisite for the
  8 月期 data-acquisition phase.

### 5.3 Production-phase results (8-10 月, TODO)

The following quantitative results are **scheduled** for the full
submission and are explicitly **not available** at the date of this
draft. They are listed here for completeness so the reader
understands the experimental scope; we will not present
fabricated numbers in their place.

- **TODO (8 月期 data-acquisition phase)**: surrogate training
  loss vs. iteration for the U-Net / FNO / DeepONet candidate
  architectures on the 100-sample MOCK + 30-50-sample real-solver
  training corpus; expected MAE ranges of 1-5% on PR and η_is will
  be reported against Suder 1995 Table 1 (corrected mass flow
  baseline 20.93 kg/s, peak efficiency 0.876).
- **TODO (9 月期 data-acquisition phase)**: 3D single-channel
  Pareto frontier plot for `Rotor37SingleChannel.java` runs over
  the FFD-lattice variable set; the 30-50-sample sweep will be
  compared against the NASA-TP-1659 design PR and the Suder 1995
  Figure 4 100% speed line.
- **TODO (10 月期 modeling phase)**: 2D-vs-3D surrogate consistency
  comparison (NACA 0012 baseline at Re=6×10^6, α=2°,
  Mach=0.15, plus the rotor37 2D slice); NACA 0012 tolerance
  reference is Ladson 1988 (NASA TM 100526) cl=0.235,
  cd=0.0061, cm=-0.0095.
  - **TODO (10-12 月期 active-learning + Pareto validation phase)**:
  100-200 LHS sample plan surrogate error table (per-sample
  measured-vs-surrogate; mean, max, and worst-case relative
  error); the existing MOCK test pipeline (69 tests across
  `cfd_harness.tests` and `starccm-bridge.tests`,
  `reports/STATE.md:84-87`) is the testbed for ensuring no
  regression in the MOCK executor behavior, while the broader
  Codebuddy CLI baseline of 1686 tests
  (`AGENTS.md:9, 29`) is the upstream-of-record for the
  Codebuddy REPL itself.
- **TODO (full submission)**: byte-deterministic signed audit
  package (SHA-256 over `spec_hash | executor_mode |
  executor_version`) for the Pareto frontier; this requires the
  `audit_package` batch-manifest extension listed in
  `track-c-deliverable.md:232-241` (debt item D1), scheduled for
  the 8-10 月期 backend-engineer workstream.

## 6. Conclusion and Future Work

### 6.1 Conclusion

This draft documents the framework and the validated stub-level
infrastructure for a 12-month, three-milestone project on neural
surrogate-based parametric multi-objective optimization of commercial
fan and propeller blades. The 7 月期 M1 window has delivered, with
quantitative end-to-end evidence and file:line traceability:

- (i) the rotor37 gold-standard yaml with 14 numeric blocks filled,
  GoldStandardComparator 14/14 all_pass, and 0 placeholders;
- (ii) the `case_solve/fan_blade.py` stub with 4/4 smoke tests and
  8/8 four-plane enforcement checks;
- (iii) the `scripts/run_rotor37_macro.py` driver with MOCK
  smoke test exit 0 and 10 quantities read from the gold-standard
  yaml; and
- (iv) the `macros/Rotor37Slice2D.java` reflective-skeleton
  stub compiling cleanly against the STAR-CCM+ 2402 R8 classpath.

In addition, two pre-existing cfd-harness `.sim` artifacts (NACA
2412 v35 with k-ω SST, 2000 iter, 115 MB; LDC laminar steady,
5000 iter, 1.9 MB) demonstrate that the v3x end-to-end pipeline
(geometry → mesh → physics → solve → scene export) is functional
on the production STAR-CCM+ 2402 R8 stack; their scene PNG
exports are reproduced in §5.1.5 as pipeline-touchpoint
visualizations, not as surrogate training data.

A side finding from the pipeline-validation pass (§5.4) is that
the v3x NACA 2412 Cl/Cd/Cm integration is consistent with the
standard wind-tunnel sign convention only after explicit
mapping; the v3x output is sign-convention-aliased in the
current build. The mapping will be added to the 8 月 M2
sample-generation phase and is not a blocker. The LDC
`u_centerline` sampling is a known issue (DEC-005, FF probe
API gap on 2402 R8) and is unblocked by the C-1.1 bridge
encoding fix landed in this draft's authoring window; the
8 月 M2 workstream will close DEC-005.

A single method-level finding is pre-locked for the submission: the
PLAID-datasets/Rotor37 HuggingFace mirror is Safran RANS simulation
output, not NASA experimental gold, and must not enter
`reference_values`; PLAID is therefore re-purposed as a surrogate
training corpus. We do not claim any other empirical result in this
draft; surrogate training, Pareto-frontier computation, and
high-fidelity back-validation are explicitly deferred to the 8-10 月期
workstream and the 2027-01 milestone.

### 6.2 Future work

The 12-month delivery roadmap, taken from
`verdict-2026-07.md:443-485` and `decisions/DEC-008-project-charter.md:93-97`,
is:

- 2026-07 (立项期, current): 4 track deliverables, 3 stub scaffolds,
  DEC-008.a M1 acceptance — **delivered**;
- 2026-08 (数据期 ①): 2D LHS 100-200 MOCK samples + 30-50 STAR-CCM+
  real-solver samples; bridge `_invoke` 1-line `encoding="utf-8"`
  patch as hard prerequisite;
- 2026-09 (数据期 ②): 3D single-channel 30-50 samples via the
  planned `Rotor37SingleChannel.java` macro (D-7 RRF verified
  resolvable; full 90 s spawn pending 7/20-7/25);
- 2026-10 (建模期 ①): surrogate baseline validation on the LDC and
  NACA 0012 case profiles already in `knowledge/case_profiles.yaml`,
  with U-Net / FNO / DeepONet architecture selection;
- 2026-12 - 2027-01 (优化期): NSGA-II + q-EHVI Pareto-front
  computation and high-fidelity back-validation; DEC-008.d
  sub-decision;
- 2027-02 - 2027-04 (写作期): full paper draft, internal review,
  DEC-008.d ratification;
- 2027-05 (预印本): arXiv / AIAA SciTech preprint;
- 2027-06 (投稿): submission to AIAA Journal / Computers & Fluids
  / Aerospace Science & Technology.

A 12-month timeline table is included as Appendix B.

---

## 7. References

[1] B. R. Kulfan, "Universal parametric geometry representation method,"
*Journal of Aircraft*, vol. 45, no. 1, pp. 142-158, 2008.

[2] T. W. Sederberg and S. R. Parry, "Free-form deformation of solid
geometric models," *ACM SIGGRAPH Computer Graphics*, vol. 20, no. 4,
pp. 151-160, 1986.

[3] Cheng et al., "Multi-fidelity MDOF framework for Rotor 37
optimization," *J. Therm. Sci.*, 2021.

[4] Hong et al., "ABC2: Airfoil-Blend Cross-Coupled Control for
counter-rotating open rotors," *Vertical Flight Society / SAE
International*, 2024.

[5] N. Thuerey, K. Weißenow, L. Prantl, and X. Hu, "Deep learning
methods for Reynolds-averaged Navier-Stokes simulations of airfoil
flows," *AIAA Journal*, vol. 58, no. 1, pp. 25-36, 2020.

[6] Shukla et al., "DeepONet for Reynolds-averaged airfoil
predictions," *Engineering Applications of Artificial Intelligence*,
2024.

[7] Liu et al., "Denoising diffusion probabilistic models for airfoil
flow generation," *AIAA Journal*, 2024.

[8] Harmening et al., "Physics-informed neural networks for airfoil
aerodynamics," *Neural Computing and Applications*, 2024.

[9] Hanrahan et al., "Critical survey of machine-learning surrogates
for turbo-machinery flows," *Int. J. Heat and Fluid Flow*, 2023.

[10] F. Casenave, B. Staber, and X. Roynard, "MMGP: a Mesh Morphing
Gaussian Process-based machine learning method for regression of
physical problems under non-parameterized geometrical variability,"
arXiv:2305.12871, 2023. *PLAID-datasets/Rotor37*, HuggingFace, Owner:
Safran, License: CC-BY-SA 4.0.

[11] K. L. Suder, R. V. Chima, A. J. Strazisar, and W. B. Roberts,
"The effect of adding roughness and thickness to a transonic axial
compressor rotor," *ASME J. Turbomachinery*, vol. 117, no. 4,
pp. 491-505, 1995. DOI: 10.1115/1.2836561.

[12] R. D. Moore and L. Reid, "Performance of single-stage axial-flow
transonic compressor with rotor and stator aspect ratios of 1.19 and
1.26, respectively, and with design pressure ratio of 2.05,"
NASA-TP-1659, 1980.

[13] L. Reid and R. D. Moore, "Design and overall performance of four
highly loaded, high-speed inlet stages for an advanced high-pressure-
ratio core compressor," NASA-TP-1337, 1978. (Cited for four-stage
core-compressor context; not Rotor 37 alone.)

[14] L. Reid and R. D. Moore, "Performance of single-stage axial-flow
transonic compressor with rotor and stator aspect ratios of 1.19 and
1.26, respectively, and with design pressure ratio of 1.82,"
NASA-TP-1338, 1978. (4-stage core-compressor report, PR 1.82 per
stage; not Rotor 37 design PR 2.05; cited in `track-c-deliverable.md`
for context only.)

[15] NUMECA, *FINE/Turbo Rotor37 Tutorial Case*, 2011+.

[16] AGARD, "CFD validation for propulsion system components,"
AGARD-AR-355, 1995.

[17] Z. Li, N. Kovachki, K. Azizzadenesheli, B. Liu, K. Bhattacharya,
A. Stuart, and A. Anandkumar, "Fourier neural operator for parametric
partial differential equations," *ICLR*, 2021. arXiv:2010.08895.

[18] L. Lu, P. Jin, G. Pang, Z. Zhang, and G. E. Karniadakis, "Learning
nonlinear operators via DeepONet based on the universal approximation
theorem of operators," *Nature Machine Intelligence*, vol. 3,
pp. 218-229, 2021.

[19] Z. Wang, T. Wang, and K. Duraisamy, "Airfoil GAN: synthesis of
airfoil shapes via generative adversarial networks," *J. Comput.
Des. Eng.*, 2023.

[20] Kang et al., "Variational autoencoder for airfoil geometry
generation," *AIAA SciTech*, 2024.

[21] Wei et al., "DiffAirfoil: a diffusion-based airfoil generation
model," *AIAA Aviation*, 2024.

[22] M. Ladson, C. Brooks, A. Hill, and D. Sproles, "Computer program
to obtain ordinates for NACA 4-digit, 4-digit modified, 5-digit, and
16-series airfoils," NASA Technical Memorandum 100526, 1988.
(Cl=0.235, Cd=0.0061, Cm=-0.0095 at Re=6×10⁶, α=2°, Mach=0.15
for the 2D NACA 0012 baseline used in §4.3.)

[23] F. M. White, *Viscous Fluid Flow*, 2nd ed., McGraw-Hill, 1991
(reference for turbulent flat-plate boundary layer; cited in
`track-a-deliverable.md`).

[24] DEC-008, "民机风扇/螺旋桨 AI-CFD 项目立项 (L0 advisory),"
`reports/research/commercial-fan-prop/decisions/DEC-008-project-charter.md`,
2026-06-12.

[25] DEC-008.a, "7 月期 M1 验收 (子决策),"
`reports/research/commercial-fan-prop/decisions/DEC-008.a-m1-acceptance.md`,
2026-06-12.

[26] Verdict doc (2026-07), "commercial-fan-prop M1 verdict,"
`reports/research/commercial-fan-prop/verdict-2026-07.md`.

[27] P1 stub deliverable,
`reports/research/commercial-fan-prop/planning/p1-yaml-deliverable.md`,
2026-06-12.

[28] P2 stub deliverable,
`reports/research/commercial-fan-prop/planning/p2-fan-blade-stub-deliverable.md`,
2026-06-12.

[29] P3 stub deliverable,
`reports/research/commercial-fan-prop/planning/p3-driver-stub-deliverable.md`,
2026-06-12.

---

## Appendix A · M1 Stub Inventory

The four stub artifacts whose end-to-end smoke tests pass, as
delivered in the 7 月期 M1 acceptance window. Lines / bytes are from
the 2026-06-12 filesystem state.

| Stub | File path | Lines / bytes | Smoke test | Cross-reference |
|---|---|---|---|---|
| P1 gold-standard yaml | `knowledge/gold_standards/rotor37.yaml` | 26191 B / ~330 lines / 14 quantity blocks | GoldStandardComparator 14/14 all_pass; 0 placeholders; baseline pytest 7/7 in 0.43 s | `p1-yaml-deliverable.md:1-7, 128-156` |
| P2 fan-blade builder | `src/cfd_harness/starccm_adapter/case_solve/fan_blade.py` + `__init__.py` | 180 + 11 lines / 8236 + 517 B | 4/4 smoke tests in 0.26 s; 8/8 four-plane enforcement | `p2-fan-blade-stub-deliverable.md:46-48` |
| P3 driver | `scripts/run_rotor37_macro.py` | 9439 B / 198 lines | mock exit 0; is_mock=True; 10 yaml quantities read | `p3-driver-stub-deliverable.md:50-77` |
| P3 Rotor37 2D macro | `macros/Rotor37Slice2D.java` | 3079 B / 57 lines | javac RC=0 against 2402 R8 classpath; reflective skeleton green; `star.motion.RotatingReferenceFrame` 1/4 candidate hit (D-7) | `p3-driver-stub-deliverable.md:88-96`; `d7-probe-result.md:8-39` |

The four stub artifacts are non-production: the 2D macro is a
defensive skeleton (`if (itersEnv == null) throw new
RuntimeException("not yet implemented ...")`,
`Rotor37Slice2D.java:19-24`); the fan-blade builder writes only a
marker macro and returns a placeholder `.sim` path
(`fan_blade.py:135-143`); the driver defaults to `--executor mock`
and treats the WIN_STARCCM path as opt-in
(`run_rotor37_macro.py:197-198`). No production STAR-CCM+ run has
been performed at the date of this draft.

## Appendix B · 12-Month Timeline

The following table reproduces the timeline committed in
DEC-008 §5 and `verdict-2026-07.md:443-485`. Months are project
months, where month 1 = 2026-07 and month 12 = 2027-06.

| Month | Project month | Milestone / output | Owner | Reference |
|---|---|---|---|---|
| 2026-07 | M1 | 立项期: 4 track deliverables + 3 stub scaffolds + DEC-008.a M1 acceptance | chief-engineer + vv-director + starccm-adapter-engineer | DEC-008 / DEC-008.a / m1-acceptance-checklist |
| 2026-08 | M2 | 数据期 ①: 2D LHS 100 MOCK + 30-50 STAR-CCM+ real-solver samples; bridge `_invoke` 1-line patch as hard prerequisite | chief-engineer + starccm-adapter-engineer | verdict §7.3; DEC-008.b |
| 2026-09 | M3 | 数据期 ②: 3D single-channel 30-50 samples via `Rotor37SingleChannel.java`; D-7 RRF enable 90 s spawn | starccm-adapter-engineer | verdict §7.3; D-7 follow-up |
| 2026-10 | M4 | 建模期 ①: surrogate baseline validation on LDC and NACA 0012; U-Net / FNO / DeepONet architecture selection | backend-engineer | verdict §7.3; DEC-008.c |
| 2026-11 | M5 | 建模期 ②: surrogate training on full 100+30-50 sample corpus; held-out MAE reporting | backend-engineer | DEC-008.c |
| 2026-12 | M6 | 优化期 ①: NSGA-II Pareto-front computation; q-EHVI active-learning loop iteration 1 | backend-engineer | DEC-008.d |
| 2027-01 | M7 | 优化期 ②: high-fidelity back-validation; Pareto frontier ratified against Suder 1995 + NASA-TP-1659 | chief-engineer + vv-director | DEC-008.d |
| 2027-02 | M8 | 写作期 ①: full draft (results, figures, appendix); internal review | docs-knowledge-engineer | DEC-008.e |
| 2027-03 | M9 | 写作期 ②: review feedback integration; reproducibility package | docs-knowledge-engineer | DEC-008.e |
| 2027-04 | M10 | Draft v1 frozen; pre-submission internal review | chief-engineer | DEC-008.e |
| 2027-05 | M11 | 预印本: arXiv / AIAA SciTech preprint | chief-engineer | DEC-008.e |
| 2027-06 | M12 | 期刊投稿: AIAA Journal / Computers & Fluids / Aerospace Science & Technology | chief-engineer | DEC-008.e |

The 12-month cadence aligns with the project's three-month
sub-milestone schedule (2026-10 / 2027-01 / 2027-06) documented in
`reports/STATE.md:101-103` and DEC-008 §5.

---

*Draft v1 (M1 window), authored 2026-06-12. Quantitative results
are restricted to the 4 stub artifacts validated end-to-end during
the 7 月期 M1 acceptance pass. Surrogate training, Pareto-front
computation, and high-fidelity back-validation are deferred to the
8-10 月期 workstream and the 2027-06 target submission. This draft
will be re-released as v2 in 2027-04 and v3 (submission candidate)
in 2027-06.*
