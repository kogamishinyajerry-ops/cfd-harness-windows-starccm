# cfd-harness-windows-starccm · methodology notes

> Cross-cutting methodology notes that don't fit AGENTS.md / STATE.md / a spec doc.
> Each note has: scope (when to read), problem, and the lesson.
> Verifier/maintainer should append here whenever a recurring pattern emerges.

---

## MM-001 · `status: proven` + `verified_by:<path>` is NOT a closed-form claim

**Scope**: any future verifier auditing `knowledge/macro_registry.yaml`
(companion to `docs/specs/MACRO_REGISTRY_SCHEMA.md`).

**Problem (2026-06-11, found during plan_b170bb32 integration-verdict)**:

15 of 18 entries with `status: proven` cited
`verified_by: packages/starccm-bridge/tests/test_bridge_p0p1p2_fixes.py`.
That test file is a pure bridge-plumbing unit-test suite (per its own
docstring: "PURE unit tests... do NOT require a STAR-CCM+ install, do NOT
subprocess anything") — it tests argv builders + error classifiers + the
`starccm_bat` heuristic, NOT the macros themselves.

The verifier's first audit (`path.exists()` on the cited path) passed
for all 18 — the test files exist. The semantic audit (does the test
actually invoke this macro?) revealed 15 misclassified.

**Lesson (for this project)**:

`verified_by: <test_path>` is necessary but insufficient. Three checks
are needed:
1. `path.exists()` → mechanical (existing).
2. **Does the cited test invoke this specific macro?** → grep the test for
   the macro's `filename` or class name. If absent, the test does NOT
   prove the macro works.
3. **Is the macro file mtime <= `verified_at`?** → if mtime is newer, the
   status is stale (5 of 53 entries failed this on 2026-06-11).

**Lesson (generalizable, see agent-memory `verifier/registry-audit.md`)**:

Whenever a registry/index schema has `status: proven` (or equivalent)
backed by a pointer to a test/audit artifact, run the **semantic
coupling check** — open the cited artifact, search for the entity's
name, and confirm it actually exercises the entity. The mechanical
"file exists" check is verification avoidance, not verification.

**Open follow-ups (for docs-knowledge-engineer)**:

- Schema §3.2 should add a `verified_by_kind: enum[pytest_real_solver |
  pytest_unit | manual_audit | state_md | other]` so the registry
  distinguishes "the bridge plumbing test exercises this macro's
  invocation surface" from "this test directly invokes this macro's
  logic and verifies its outputs". Until then, the verifier must do
  this manually per-entry.
- The drift linter (option II from verdict.md §4.2) catches
  `mtime > verified_at` automatically — implement when chief-engineer
  picks precondition2.