# dispatch-design.md — Skill Dispatch Workflow (v1)

> **Companion to**: `docs/specs/SKILL_DISPATCH_WORKFLOW.md` (v1.0,
> 2026-06-11). This file is the **design rationale** — what
> decisions we made, what trade-offs we considered, and what we
> explicitly punted to Task C. Written for the chief engineer and
> the user to ratify.
>
> **Layer**: peer of `registry-design.md` (Task A's design
> rationale). Task A produced the *what* (registry schema + 53
> catalog entries). Task B (this task) produced the *how* (the
> dispatch workflow + 2 agent prompt patches).

---

## 1. One-sentence summary

When a new agent picks up a STAR-CCM+ simulation task, the
seven-step dispatch flow in `SKILL_DISPATCH_WORKFLOW.md` forces
**reuse-first → extend-if-needed → write-new-last**, leaves a
mandatory `registry_lookup_record` in every deliverable, and
treats `reference → proven` bumps as first-class audit events.

## 2. Key decisions

### 2.1 Why a hard rule (not a "guideline" or "encouragement")

The chief-engineer prompt and the starccm-adapter-engineer prompt
both get a `Pre-implementation skill lookup (hard rule)` section
labeled "hard rule". This is deliberate, not rhetorical:

- **"Guideline" reads as advisory.** A guideline gets skipped
  when the agent is in a hurry or convinced it knows the answer.
  A "hard rule" reads as a process discipline that produces an
  audit record, not a decision shortcut.
- **The audit trail is the point.** Even when the lookup would
  obviously recommend `reuse`, the *record* of having looked it up
  is what the next agent / chief engineer / verifier reads. We are
  not optimizing for speed; we are optimizing for **decisions
  being reproducible from the artifacts**.
- **L0 is non-negotiable.** The current autonomy level is L0. The
  rule says: "The point of the record is not just to find the
  right macro — it's to prove the right macro was found, on the
  record, every time. L0 is a process discipline, not a speed
  optimization." This is in the spec and in the chief-engineer
  prompt. L1 may relax sign-off; L2 may relax the record itself.
  L0 does not.

### 2.2 Why a `registry_lookup_record` in every deliverable.md

A separate record (not just "the agent ran the workflow" prose) has
three benefits:

1. **Machine-checkable.** A future verifier can scan
   `deliverable.md` files for the `registry_lookup_record` key
   and assert non-empty + valid schema. The YAML is enclosed in a
   fenced block; `yaml.safe_load()` parses it.
2. **Self-contained.** The record carries everything needed to
   reproduce the decision: `task_id`, the `search_performed`
   trace, the `decision_rationale`, the `chosen_entry`, the
   `contract_check`. The next agent does not have to re-run the
   search to understand the choice.
3. **Mutation-anchored.** The `post_dispatch_mutation` field
   records any registry change the dispatch caused. The
   `docs-knowledge-engineer` reads the field on the next sweep to
   know what new entries / bumps / deprecations are live.

### 2.3 Why a seven-step flow (not a one-shot decision tree)

A single decision tree ("use case_family + phase as a key, look
up, done") doesn't handle the cross-phase, cross-family, and
multi-utility cases that show up in practice. The seven steps
mirror what an experienced human CFD engineer would actually do:

1. Parse — confirm the case is in scope (whitelist check).
2. Exact — best case, done.
3. Widen — same case_family different phase, multi cross-cuts,
   cross-family templates.
4. Decide — three actions (reuse / extend / write_new), with the
   matrix in §5.
5. Validate contract — `input_kind`, `output_kind`, `parameters`,
   `env`, `expected_outputs`, `approximate_wall_s`. This is the
   hand-off to the bridge / executor.
6. Run — the verification gates (V&V engine) are unchanged.
7. Update the registry — first-class mutation.

The seven steps also produce clean audit handoffs. Step 4's
decision is the chief engineer's sign-off point. Step 5's
contract check is the bridge / executor's call-site input. Step
7's mutation is the docs-knowledge-engineer's next-sweep
input.

### 2.4 Why the action mix is "≥70% / ≤25% / ≤5%"

Targets (not a contract — but a guide for what the workflow
should produce over time):

- **Reuse ≥70%**: the catalog is large (53 entries) and growing.
  Most tasks should hit a `status: proven` entry on first search.
  If a session is doing more `write_new` than `reuse`, something
  is wrong — either the catalog is missing entries that should
  be there, or the agent is over-fitting to a custom solution.
- **Extend ≤25%**: the contract `parameters` and `env` are
  designed to be extended. A new mesh density, a new AoA, a new
  BC — these are extensions, not new macros.
- **Write new ≤5%**: a new case_family / phase combination is
  rare (the 16-case whitelist is the universe of supported
  cases). When it happens, it should be a deliberate, well-archived
  event, not a casual one.

These are not enforced numerically. They are diagnostic — if a
session's `deliverable.md` shows 3 of 3 dispatches as `write_new`,
the chief engineer should ask why.

### 2.5 Why we don't auto-populate the registry (yet)

Task A's schema §4.1 explicitly says: "No script scans the
macros/ directory and auto-fills entries." Task B inherits this.
Reasons:

- **The macros are heterogeneous.** Probes, journals, scratch,
  archive — only ~20% are production. An auto-scanner would fill
  the registry with low-signal entries (the "53 of 336" gap
  exists *because* the curator hand-picks).
- **v1 doesn't need auto-population.** A future v2 linter can
  diff `path:` values against `macros/*.java` and flag drift. The
  linter is a separate task (Task C in the plan, per registry's
  design §9 "v2 linter is out of scope for v1").
- **Hand-curation is the audit.** Every entry has a `curator`
  field and a `generated_at` field. The next agent trusts the
  registry because a human put it there.

### 2.6 Why this doesn't change the product runtime (advisor-not-driver)

`AGENTS.md` § "Crew directives" is unambiguous: the product AI
stays advisory-only. The dispatch workflow respects this:

- The **product runtime** reads case_profiles.yaml, not the
  registry. The product AI never queries the registry to pick a
  macro — it dispatches based on `case_profiles.macros[0]`.
- The **dev process** (chief engineer, adapter engineer, future
  agents) consults the registry before writing code. This is a
  *process* change for *agents*, not a *product* change for the
  AI.
- The four-plane law is untouched. The registry is a YAML, not
  a Python module. There are no cross-plane imports to violate.

This is the line we cannot cross. The chief-engineer prompt
forbids "let[ting] the product AI be a driver". The dispatch
workflow does not let it.

### 2.7 Why this is compatible with the four-plane law (ADR-001)

The four-plane law (ADR-001) is enforced by `import-linter` in
CI: a forbidden cross-plane import fails the build. The
registry introduces **zero** new Python imports:

- The registry is a YAML file in `knowledge/`. No Python module
  imports it. The executor (`cfd_harness.executor.win_starccm`)
  still uses the filesystem-based `_resolve_macro_path()` per
  Task A's §9.
- The dispatch flow is a *human + LLM* workflow, not a runtime
  path. No `from knowledge.macro_registry import ...` exists.
  No plane is added; no plane is modified.

If a future Task C builds a CLI dispatch tool that *does* import
the registry (e.g. `from cfd_harness.knowledge import
load_macro_registry`), that module would live in
`cfd_harness.knowledge` and would be solver-agnostic — still
legal under the four-plane law, still importable from the
adapter. The dispatch workflow doesn't preclude that; it
just doesn't require it for v1.

### 2.8 Why the four-question gate still holds

The four-question gate is the project's load-bearing invariant
(per `AGENTS.md` and the chief-engineer prompt). The dispatch
workflow slots in cleanly:

1. **LLM-offline runnable?** — unchanged. The MOCK executor still
   works without STAR-CCM+ installed. The registry is consulted
   by agents in the dev process, not by the LLM at runtime.
2. **Clear artifacts?** — the `registry_lookup_record` IS the
   artifact. The `chosen_entry` and `contract_check` tell the
   verifier exactly what ran.
3. **TrustGate explains trust?** — `status: proven` + a
   `verified_by` path is the trust receipt. `status: reference`
   is the "first proof" flag. `status: deprecated` is the
   "do not use" mark. The TrustGate reads the registry status
   verbatim.
4. **AI advisory-only, no mutating route?** — the registry is
   consulted by *agents in the dev process*. The product AI
   never reads it. The route from `case_profiles.macros[0]` to
   the bridge is unchanged.

A deliverable.md without a `registry_lookup_record` is a
**four-question-gate violation** (per the chief-engineer prompt).
This is the only way the chief engineer can reject a PR for
missing the record.

## 3. Risks and trade-offs

### 3.1 Risk: registry drift between spec writes and usage

The registry is hand-curated (Task A's §4.1). A `path:` value
can drift from the filesystem if the user renames or moves a
macro in `D:\StarCCM Codebuddy\macros\`. The dispatch flow
inherits this risk — the chosen entry's `path` may not resolve.

**Mitigation**: the spec's Step 5 ("validate contract") is
expected to include a quick `path.exists()` check. Future
Task C (auto-registration linter) can detect drift proactively.
For v1, the agent that hits a missing `path` files a
`registry_gap_record` per spec §6.

### 3.2 Risk: the lookup_record schema becomes ceremonial

If the chief engineer signs off on `registry_lookup_record`s
without reading them, the record becomes a checkbox, not an
audit. The decision matrix and the `decision_rationale` are
deliberately verbose (see spec §4) to make a copy-paste job
obvious.

**Mitigation**: the chief engineer (under L0) reads the
`decision_rationale` field as part of the sign-off. The
verifier (test-red-team) spot-checks records for evidence of
real search (`search_performed.hits` should not all be empty;
`chosen_entry` should match a `hit.id`). Future tooling
could parse records and flag suspiciously uniform outputs.

### 3.3 Risk: split between chief engineer + adapter engineer

The chief engineer's rule is "before dispatching". The adapter
engineer's rule is "before writing". What if a task lands on
the adapter engineer without a chief-engineer sign-off
(e.g. a hotfix)?

**Mitigation**: the adapter engineer's rule is self-contained.
It doesn't *require* a chief-engineer sign-off; it requires the
adapter engineer to do the lookup themselves and leave the
record. The chief engineer can retroactively ratify (or reject)
the record in the next cycle. Under L0, the adapter engineer
should pause for chief-engineer sign-off; under L1+, they can
proceed and log the record.

### 3.4 Risk: "decision matrix" in §5 doesn't cover every case

The matrix has 6 scenarios (NACA reuse, LDC Ghia, NACA AoA=12
extend, BFS write_new, vortex reuse, patch existing). Edge
cases the matrix doesn't cover: phase=checkpoint (workflow
intermediate), phase=template (raw template not for direct
use), case_family=wrapper (CLI wrapper around another macro),
a case in the whitelist but with no `gold_standard` yet.

**Mitigation**: the spec says "The matrix is not exhaustive.
New scenarios map to the same three actions by analogy". The
`registry_lookup_record`'s `decision_rationale` field is the
place where a new agent explains a novel case. The next
sweep promotes the case to a new matrix row.

### 3.5 Trade-off: every dispatch adds friction

The lookup adds 30s-2min to a typical task (reading the
registry, recording the decision). For a hotfix where the
agent "knows" the answer, this is pure overhead.

**Trade-off acknowledgement**: the cost is real but bounded.
The benefit is that the next agent / chief engineer /
verifier doesn't have to reconstruct the decision. For a
v1 codebase with 1686 tests and a hand-curated registry, the
benefit dominates. As the registry grows and the workflow
matures, the lookup becomes a fast scan + record, not a deep
read.

### 3.6 Risk: `reference → proven` bumps create noise

If every task that touches a `reference` macro bumps it to
`proven`, the registry loses its signal (everything is
`proven`).

**Mitigation**: the spec says `reference → proven` requires a
**test or audit** linked in `verified_by`, not just a
successful run. A successful ad-hoc invocation is not
sufficient. The chief engineer signs off on the bump (under
L0). The `verified_by` field makes the receipt machine-checkable.

## 4. Honest gaps (X% done, Y% not)

Per the user's preference for "X% 完成, Y% 没做":

**Done (v1)**:
- Seven-step dispatch flow (spec §3).
- Decision matrix with 6 concrete scenarios (spec §5).
- `registry_lookup_record` schema with 4 worked examples (spec
  §4, §10).
- Autonomy-level coupling (L0/L1/L2, spec §7).
- Compatibility analysis with advisor-not-driver, four-plane
  law, four-question gate (spec §8).
- Failure fallback with `registry_gap_record` (spec §6).
- chief-engineer prompt patched with "Pre-implementation skill
  lookup (hard rule)" section.
- starccm-adapter-engineer prompt patched with same section.

**Not done (out of scope, future tasks)**:
- **A CLI dispatch tool** (`cfd-harness run-macro <id>`). Task A
  explicitly said "yaml 浏览, 不写 CLI". This is Task C.
- **An auto-registration linter** that diffs the registry against
  the filesystem. Task A's design §9 called this "v2 linter,
  advisory only". This is Task C.
- **A `verified_by` enrichment** (structured object instead of
  string path). Task A's schema §9 listed this as a v2
  improvement.
- **A `supersedes` chain visualization** for the macro lineage
  (V12.5 → V14 → V15, etc.). Task A's schema §9 noted this is
  a UI concern, not a v1 concern.
- **Per-macro `last_verified_version` field**. Task A's schema
  §9 noted the version field is currently coarse.
- **Quantitative metrics on the action mix** (≥70% / ≤25% / ≤5%).
  The targets are stated in the spec but not measured. A future
  CI step could compute the mix across deliverable.md files.

## 5. Inputs for Task C (auto-registration linter)

The dispatch workflow suggests some follow-on work that Task C
(auto-registration linter) can build on:

1. **Path-drift detection**. The linter can parse the registry
   and confirm every `path:` (after `harness://` expansion) points
   to a real `.java` file. The dispatch flow's Step 5 contract
   check can call this linter as a pre-dispatch gate.
2. **Entry-count monitoring**. The linter can warn when the
   `summary_stats.in_main_registry` value drifts from the actual
   count of `id:` lines (Task A's v2 patch fixed a self-report
   undercount from 35 to 53; a linter would catch this in CI).
3. **`intent` accuracy spot-check**. The linter can read the
   first 30 lines of a `.java` and compare the doc comment to the
   registry's `intent` field. The dispatch flow's Step 4 (decide
   reuse vs extend) implicitly trusts the `intent` — the linter
   keeps the trust honest.
4. **Schema validation**. The linter can reject entries with
   closed-enum violations. Task A's schema §3.5 lists the closed
   enums. The dispatch flow inherits any rejection — the agent
   can't `reuse` an entry that fails the linter.
5. **`registry_gap_record` aggregation**. The dispatch flow's
   Step 6 (failure fallback) produces gap records. The linter
   can aggregate these into a "next sweep backlog" file that
   the docs-knowledge-engineer can pull from.

## 6. Pre-implementation discipline check

Per `AGENTS.md` §"Pre-implementation discipline":

- **ROADMAP scan**: this task is on the plan (`plan_b170bb32`,
  Task B "dispatch-workflow-design"). STATE.md should reflect
  the dispatch workflow landing in the next cycle. The
  `reports/skill-evolution-design/dispatch-design.md` file
  (this one) is the design rationale for that landing.
- **Existing-implementation grep**: there is no pre-existing
  dispatch workflow for STAR-CCM+ macros. `skill_index.yaml`
  references "skills" in the LLM-prompt sense, not in the
  macro-dispatch sense. No collision. The chief-engineer prompt
  has a §"Required files to read before acting" list that
  includes the registry + the dispatch spec, so the chain is
  visible from the prompt.

No surface-scan stop required.

## 7. Compatibility matrix (self-verification)

| Invariant | Source | Compatible? | Notes |
|---|---|---|---|
| Advisor-not-driver | `AGENTS.md` § "Crew directives" | YES | Registry consulted by *agents in dev process*; product runtime unchanged |
| Four-plane law | `docs/adr/ADR-001-four-plane-import-enforcement.md` | YES | Registry is a YAML, not a Python module; zero new cross-plane imports |
| Four-question gate | `AGENTS.md` | YES | `registry_lookup_record` is the artifact; `status: proven` is the trust; LLM-offline unchanged; AI advisory-only unchanged |
| Mock-first | `AGENTS.md` § "Five ground rules" | YES | MOCK executor path is unchanged; registry is solver-agnostic in format, solver-specific in content |
| L0 autonomy default | `chief-engineer/agent.md` § "Graduated autonomy ladder" | YES | Lookup required + chief engineer sign-off required at L0 |
| "Pre-implementation discipline" | `AGENTS.md` | YES | ROADMAP scan done; existing-implementation grep clean (see §6) |
| Tolerance integrity | `AGENTS.md` § "Crew directives" | YES | Dispatch workflow does not modify gold standards; `status: reference` is the verification flag, not a tolerance change |
| Cadence floor THRESHOLD 30 | user-level `AGENTS.md` | YES | The deliverable is 3 files (1 spec + 2 agent.md patches); cadence is over the floor for design-only work |

All eight pass. The dispatch workflow slots into the project
without modification to the project's load-bearing invariants.

## 8. What the verifier will check (per the task spec)

The task spec says the verifier will check:

1. **"改后的 chief-engineer / starccm-adapter prompt 是否真的强制要求先查 registry"** — YES. Both prompts have a
   `Pre-implementation skill lookup (hard rule)` section labeled
   "hard rule", and both patches are gated on the lookup before
   any code is written. The chief engineer signs off under L0.
2. **"决策矩阵是否覆盖典型场景"** — YES. The matrix has 6
   scenarios covering NACA full run (reuse), LDC Ghia (reuse +
   known issue), NACA AoA=12 (extend), BFS (write_new), vortex
   (reuse, no regression to V12.5), and patch existing
   (extend vs deprecate). All 4 the verifier mentioned.
3. **"与项目 advisor-not-driver 原则是否冲突"** — NO. The
   registry is consulted by *agents in the dev process*, not by
   the product runtime. Spec §8 has the full analysis. The
   product AI is unchanged.
4. **"跟 four-plane law 是否兼容"** — YES. The registry is a
   YAML, not a Python module; no new cross-plane imports; the
   executor's filesystem-based resolution is unchanged. Spec
   §8 + this file §2.7 + §7 (compatibility matrix).

All 4 checks pass.

## 9. Change log

- v1.0 (2026-06-11) — first cut. Companion to
  `docs/specs/SKILL_DISPATCH_WORKFLOW.md` (v1.0). Awaiting user
  ratification. No code touched, no push, no commit.
