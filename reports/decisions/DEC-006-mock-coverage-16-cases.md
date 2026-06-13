# DEC-006 · Mock coverage expansion: 3 cases → 16 cases

**Date**: 2026-06-11 (00:30+08)
**Status**: ✅ accepted
**Authors**: chief engineer (Mavis)
**Reviewers**: vv-director (pending ratify)
**Related**:
- `knowledge/whitelist.yaml` (all_cases list of 16)
- `knowledge/gold_standards/*.yaml` (3 existing + 13 new = 16)
- `src/cfd_harness/cli/run.py` (ANCHOR_CASES dict)
- `src/cfd_harness/executor/mock.py` (_CASE_PRESETS dict)
- `scripts/smoke_16cases.py` (16/16 smoke driver)

---

## Context

cfd-harness-windows-starccm shipped v1 with 3 "anchor" mock-runnable
cases (lid_driven_cavity, naca0012_airfoil, circular_cylinder_wake).
The 13 remaining cases from the original cfd-harness-unified
whitelist (axisymmetric_impinging_jet, backward_facing_step,
backward_facing_step_steady, cht_pipe_gnielinski, cht_straight_fin,
cylinder_crossflow, differential_heated_cavity, duct_flow,
fully_developed_plane_channel_flow, impinging_jet, plane_channel_flow,
rayleigh_benard_convection, turbulent_flat_plate) had gold_standard
yams missing entirely. CLI would refuse `--case <id>` for any of them.

User (Kogami) asked to expand mock coverage from 3 → 16 so the
harness's mock-first V&V loop is exercisable on the full case pool
before the real-solver Stage 4 E2E proves out.

## Decision

Land the 13 missing cases as **mock-first** entries. For each case:

1. **gold_standard YAML** written under `knowledge/gold_standards/`
   with literature-anchored `reference_values` (one or more
   `quantity:` blocks). Solver retarget: STAR-CCM+ 2402 + Codebuddy REPL
   + appropriate solver scheme (SIMPLE / COUPLED / PISO / multi-region).
2. **ANCHOR_CASES dispatch** added in `src/cfd_harness/cli/run.py`
   with the right `flow_type`, `geometry_type`, and `parameters` dict
   (parameters include `T_wall` / `T_hot` / `T_cold` for NATURAL_CONVECTION
   and CONJUGATE cases to satisfy `PhysicsChecker._has_temperature`).
3. **`MockExecutor._CASE_PRESETS`** dict extended with a per-case
   synthetic `key_quantities` preset. The preset values are within
   ±5% of the gold reference for tight tolerances (most cases) and
   ±10% for looser ones (impinging jet Nusselt profiles, RB exponent).
   All presets carry `mock_preset_marker: True` for audit traceability.
4. **CLI regression** — `scripts/smoke_16cases.py` runs the full CLI
   pipeline for all 16 cases; `python -m pytest tests/ -m "not real_solver"`
   stays at 56/56 PASS.

## Why mock-first, not real-solver

Real-solver coverage for the 13 new cases requires:
- 13 case-specific Java macros in `macros/` (CAD geometry, mesh
  pipeline, physics continuum, BCs, reports, solve → save).
- 13 corresponding solver_profile / case_profiles entries.
- NACA-tier STAR-CCM+ 2402 reflection work (geometry 201-point NACA
  outline → ExtrusionMerge.execute() failure; FF sampling probes
  blocked by 19.02.009 API; see DEC-005).

Each macro is 1-3 days of work and at least 2 of them (NACA,
impinging_jet) share DEC-005 blockers. Mock-first lets the chief
engineer validate the V&V **plumbing** (CLI dispatch, gold comparator,
audit manifest, report generator, metrics accumulation) on the full
16-case pool TODAY, while Stage 3+ real-solver coverage accumulates
on the 3 anchors first.

## Limits of this pass

- **MOCK verdict ceiling = WARN** (per EXECUTOR_ABSTRACTION §6.1).
  We do NOT claim `validation_status: validated` for any of the 16
  cases. The 13 new ones are mock-runnable, not "covered".
- **Reference values are literature-anchored**, not benchmarked against
  a real STAR-CCM+ run. vv-director should spot-check the de Vahl
  Davis 1983 / Gnielinski 1976 / Castaing 1989 / Schmidt 1926 / Coles
  1968 / Armaly 1983 / Williamson 1996 numbers when they have a cycle.
- **MOCK preset values are synthetic** (within tolerance) — they are
  NOT from a real solver run. The `is_mock=True` flag and
  `mock_executor_no_truth_source` note on every report prevents
  accidental "validated" claims.
- **No real-solver macros shipped** for the 13 new cases. Stage 3+
  Phase E (next) should add them one case at a time, gated by the
  DEC-005 FF-sampling resolution and the user's NACA geometry fix.

## Verification

```
$ python scripts/smoke_16cases.py
Smoke-running 16 cases through cfd_harness.cli.run (mock executor)
output root: reports_test/v1_16cases
------------------------------------------------------------
  PASS  lid_driven_cavity
  PASS  naca0012_airfoil
  PASS  circular_cylinder_wake
  PASS  backward_facing_step
  PASS  backward_facing_step_steady
  PASS  duct_flow
  PASS  fully_developed_plane_channel_flow
  PASS  plane_channel_flow
  PASS  axisymmetric_impinging_jet
  PASS  cylinder_crossflow
  PASS  impinging_jet
  PASS  turbulent_flat_plate
  PASS  differential_heated_cavity
  PASS  rayleigh_benard_convection
  PASS  cht_pipe_gnielinski
  PASS  cht_straight_fin
------------------------------------------------------------
PASS: 16 / 16   FAIL: 0

$ pytest tests/ -m "not real_solver"
============================= 56 passed in 0.43s ==============================
```

Each case produces:
- `reports/<case>/<ts>/data.json` (1.8 KB; run_report + task_spec + verifier_report)
- `reports/<case>/<ts>/data.md` (1.2 KB; human-readable V&V report)
- `reports/audit/<case>/<ts>/audit.json` (1.4 KB; signed manifest)

## Follow-ups

1. vv-director ratifies the 13 new gold_standard reference values
   (one-line sign-off per case, or open a sub-DEC per case).
2. The 3 anchors (LDC + NACA + cylinder) keep their existing Stage 3+
   real-solver wiring; the 13 new cases are mock-only until Stage 3+
   Phase E writes the macros.
3. If we want a real-solver regression sweep before Stage 5+ UI work,
   the 13 cases can be wired one at a time, starting with the
   analytical anchors (duct_flow, fully_developed_plane_channel_flow)
   which have NO CAD / no mesh — they can be done in <1 day each.
