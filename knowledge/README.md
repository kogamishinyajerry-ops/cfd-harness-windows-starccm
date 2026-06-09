# knowledge/

The V&V corpus of cfd-harness-windows-starccm.

## What's in here

| File / dir | Purpose |
|---|---|
| `whitelist.yaml` | canonical case list (3 anchors + 17 total). The chief engineer's Stage 4 E2E iterates over the 3 anchors. |
| `attestor_thresholds.yaml` | the auto-verifier's tolerance + residual floors. Per-case overrides. |
| `skill_index.yaml` | the orchestrator's skill registry. Categories: `model_routing`, `cfd_harness`, `starccm` (Stage 3+), `architecture`. |
| `gold_standards/*.yaml` | one YAML per canonical case, anchored to literature. The reference values are solver-agnostic; only the `solver_info` block is solver-specific. |
| `schemas/` | Pydantic / TypedDict shapes for the gold standards + auto-verifier. |
| `workbench_basics/` | (Stage 3+) supplementary knowledge — physics primers, mesh advisories, solver-selection guides. |

## The literature-anchored V&V philosophy

A gold standard answers three questions, all anchored to a published paper:

1. **What does the benchmark measure?** (eg. u_centerline on the lid-driven cavity)
2. **What value does the literature give it?** (Ghia 1982 Table I)
3. **What tolerance is acceptable?** (typically 5% relative, with case-specific overrides)

The `reference_values` field in each gold standard is **literature-anchored
and solver-agnostic**. The auto-verifier compares the run's
`key_quantities` against these values; a MOCK run can never reach
`validation_status: validated` (per EXECUTOR_ABSTRACTION §6.1), but the
comparator logic is identical for MOCK and real-solver runs — only the
verdict ceiling differs.

## Stage 1+2 status

- 3 anchor gold standards ported: `lid_driven_cavity`,
  `naca0012_airfoil`, `circular_cylinder_wake`.
- 14 remaining cases deferred to Stage 2.5 (port on demand).
- Stage 3+ will retarget `solver_info` for STAR-CCM+ 2402 in each
  case (the port's `solver_info` block is the only STAR-CCM+-specific
  piece of a gold standard).

## See also

- `docs/specs/EXECUTOR_ABSTRACTION.md` — the executor contract.
- `docs/adr/ADR-001-four-plane-import-enforcement.md` — the four-plane law.
- `.harness/reins/docs-knowledge-engineer/agent.md` — who owns this dir.
- `.harness/reins/vv-director/agent.md` — who vetoes tolerance changes.
