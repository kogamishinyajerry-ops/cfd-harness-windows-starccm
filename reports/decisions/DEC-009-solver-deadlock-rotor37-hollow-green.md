# DEC-009 — NACA solver deadlock + Rotor37 hollow-green (real-solver debt)

- **Status:** accepted (debt registered) — 2026-06-13
- **Numbering note:** STATE.md Stage-4 rows and `DEC-007-NACA-v4/v5`
  reference a "DEC-008 (pending)" / "DEC-008a/b/c" for the **solver
  deadlock**. That number was later taken by the unrelated
  `commercial-fan-prop` charter (`reports/research/commercial-fan-prop/
  decisions/DEC-008-project-charter.md`). This file (**DEC-009**)
  resolves the collision: all "DEC-008 solver-deadlock" references should
  be read as **DEC-009**.
- **Related:** DEC-005 (read-back dead-end), DEC-007 (NACA closed loop).

## Context

Two distinct real-solver execution defects, both surfaced during the
NACA / Rotor37 work, neither root-caused:

### 1. NACA solver deadlock (intermittent)
`NacaTrueE2E.java` path9 mesh works — `def.get(star.meshing.BaseSize).setValue(0.05)`
with read-back confirmation, mesh built in ~69 s. But on some runs the
**solver hangs after init** at `set steps`, killed twice with a
declining-CPU signature (23.74 → 23.67 over the last 60 s — a loop
waiting on per-iter CFL/AMG convergence). Evidence:
`DEC-007-NACA-v4-mesh-path9-hang.md`, `DEC-007-NACA-v5-confirm-hang.md`.

**Important:** the hang is **intermittent / mesh-quality-dependent**, not
a hard wall — later versions (`DEC-007-NACA-v6/v7`) report 200-iter runs
**completing** in ~700–1100 s. So it is tractable, but no root-cause fix
landed.

### 2. Rotor37 hollow-green
`macros/Rotor37Slice2D.java` prints `DONE` and exits 0 while solving
**nothing**: `rotor37_slice_v7_run.log` shows "No input parts selected",
"There is no volume mesh to solve on in region Region 2", all 9 boundary
reports "Field function is not set", Pressure avg = −6.7e-11. Root cause:
it still uses the **dead** mesh path
`AutoMeshDefaultValuesManager.setValue(double)` (NoSuchMethod in 2402 R8)
instead of the working `def.get(star.meshing.BaseSize).setValue` path
proven in NacaTrueE2E.java. Its geometry is also an LDC placeholder, not
real Rotor37.

## Decision

Both are **registered debt**, explicitly **out of scope** for the
mock-first stabilization pass (they require long, hang-prone real
STAR-CCM+ runs). Until fixed:

- **Do NOT claim Rotor37 "run OK".** `exit-0 ≠ solved`. STATE.md must
  caveat the Rotor37 milestone as a hollow green (the macro reports DONE
  while the solve failed).
- Any real run that exercises these paths must be **time-boxed**
  (`--timeout`) to avoid an indefinite hang.

## Mitigations (specified, never run)

- **NACA deadlock** (was DEC-008a/b/c): try a coarser 0.1–0.2 m base
  mesh; add explicit CFL / under-relaxation ramp on the first iterations;
  attach a per-iteration status listener so a hang is detected
  deterministically instead of by wall-clock guess.
- **Rotor37 hollow-green:** port the proven NACA `BaseSize.setValue` +
  `Prism*` mesh path into `Rotor37Slice2D.java`, then add a **hard
  post-condition gate** — assert a volume mesh exists *and* a field
  function is set before printing `DONE` — so exit-0 implies a real
  solve. (Real Rotor37 geometry is separately blocked; see the
  commercial-fan-prop M2 verdict — the 2402 R8 surface→meshable-part
  conversion is GUI-only.)

## Consequences
- These items do not block the mock-first invariant or the surrogate
  (M3) track, which sidesteps the macro path entirely.
- A future real-solver session should pick exactly one mitigation,
  time-box it, and update this file with the outcome.
