# SKILL_DISPATCH_WORKFLOW · v1.0 (cfd-harness-windows-starccm)

> **Status**: v1.0 (2026-06-11) — first cut, companion to
> `knowledge/macro_registry.yaml` + `docs/specs/MACRO_REGISTRY_SCHEMA.md`.
>
> **Audience**: any agent (chief-engineer, starccm-adapter-engineer,
> backend-engineer, future session) that picks up a new STAR-CCM+
> simulation task and must decide **"do I reuse an existing macro, tweak
> one, or write one from scratch?"**
>
> **Layer**: this is a *workflow / policy* doc — it sits *above* the
> registry (which catalogs *what exists*) and *below* the executor
> (which *calls* macros). It does not import from the registry, it
> directs humans + LLMs to read it.

---

## 1. Purpose

`D:\StarCCM Codebuddy\macros\` holds 336 STAR-CCM+ Java macros as of
2026-06-11. The catalog is heterogeneous — production E2E builds,
probes, diagnostics, scratch, archives. A new agent picking up a task
must not start writing a new macro before knowing what already exists.

`macro_registry.yaml` answers "what's in the catalog?". This doc
answers "**how do I decide what to use, what to modify, and what to
write from scratch**?" — and how to leave an audit trail for the next
agent.

Goals:

1. **Reuse first, write last.** The cheapest correct macro is the one
   that already exists. Aim: ≥70% of new tasks pick `status: proven`
   directly, ≤25% extend a `status: reference` macro, ≤5% write from
   scratch.
2. **Decisions are auditable.** Every dispatch decision is recorded in
   the task's `deliverable.md` as a `registry_lookup_record`. The next
   agent reading that record should be able to reproduce the decision
   without re-running the search.
3. **Status upgrades are first-class.** A `reference` macro that
   passes a real run is bumped to `proven` — and the agent who bumped
   it left the receipt (`verified_by`, `verified_at`).

## 2. Trigger conditions — when MUST I look up the registry?

The default is: **any task that touches STAR-CCM+ must consult the
registry before writing code.** A non-exhaustive list of triggers:

| Trigger | Examples | Why consult? |
|---|---|---|
| Agent receives a new `TaskSpec` for a STAR-CCM+ case | "Run NACA 2412 at AoA=2°", "Compute LDC Ghia 1982 sampling" | Avoid building a new E2E when `lid_driven_cavity_e2e` / `naca_2412_e2e_v1` already does it |
| Agent is about to write a new `.java` macro | "I'll add `MyProbe.java`" | Check if a similar probe already exists (`cli_probe_v16`, `cli_introspect`) |
| Agent is about to write a new Stage 3+ adapter function | `run_macro("MyNewCase", ...)` | Check `case_profiles.yaml` and the registry for the case_family |
| Agent is about to copy-paste a macro | "Just take `NacaTrueE2E.java` and tweak the Re" | The registry's `supersedes` chain flags the canonical path |
| Agent is debugging a STAR-CCM+ API issue | "Why doesn't `getValue(coord)` work?" | `cli_diag_mesh_api`, `cli_introspect` are the canonical reflective probes |

**Skip clauses** (when the registry is **not** consulted):

1. The task is pure LLM-offline work (e.g. V&V engine unit tests, audit
   package signing) — no solver call, no macro needed.
2. The task is a doc-only or knowledge-only edit (per `AGENTS.md` §
   "Pre-implementation discipline" skip clause CLASS-1 docs-only).
3. The task is `MOCK` executor work (the MOCK path doesn't go through
   the macro registry at all — it's a separate code path).
4. The chief engineer explicitly says "skip registry" with a one-line
   reason in the `deliverable.md` (e.g. "truly trivial stub update,
   single line, no new top-level file").

**Even with a skip clause, the deliverable.md MUST contain a
`registry_lookup_record` field** with `status: skipped` + the reason.
Auditability over silent omission.

## 3. The seven-step dispatch flow

When a trigger fires, the agent walks this flow. Each step has a clear
output that flows into the next step and into the deliverable.

### Step 1 — Parse the TaskSpec

Extract:

- **`case_id` / `case_family`** (e.g. `naca0012_airfoil`)
- **`phase`** (e.g. `full_pipeline`, `postprocess`, `mesh`)
- **`intent`** — a one-sentence description of what success looks like
  (e.g. "Run NACA 2412 Re=6e6 AoA=2°, get Cl/Cd within Ladson 1988
  tolerance")
- **`mesh_density` / `iterations` / other parameters** — used in
  Step 5 to pick the right contract config

If the `case_id` is not in `knowledge/whitelist.yaml:all_cases`, STOP.
The task is out of scope. Surface to the user with the standard
"out-of-whitelist" disposition (per `AGENTS.md` §
"Pre-implementation discipline").

### Step 2 — Initial exact lookup

Query the registry:

```yaml
filter: case_family == '<case_family>' AND phase == '<phase>'
```

Three outcomes:

**(A) Exact match exists, `status: proven`** — best case. The macro
has been smoke-tested or E2E-tested. Record the `id` and go to Step 5
(dispatch).

**(B) Exact match exists, `status: reference`** — usable but
unverified. Record the `id`, go to Step 5, and **flag the run as
"first proof"** — if it passes, the agent must update the registry
entry to `proven` (Step 7).

**(C) Exact match exists, `status: deprecated`** — DO NOT USE. The
entry is archived; `superseded_by` points to the current canonical
version. If the successor is also in the registry, switch to that
entry. If not, surface to the chief engineer.

**(D) No exact match** — go to Step 3 (fuzzy / same-case-family
search).

### Step 3 — Fuzzy / same-case-family / cross-phase search

If no exact match, widen the search:

**(a) Same case_family, different phase** — e.g. the task is
`naca0012_airfoil + postprocess` but the registry only has
`naca0012_airfoil + full_pipeline` (`naca_2412_e2e_v1`). Decision:
**chained dispatch** — call the full_pipeline to (re)build the sim,
then call a `postprocess`-phase macro on the result.

**(b) Same case_family, multi-phase** — the task is
`naca0012_airfoil + mesh` but the registry only has the E2E. The E2E
macro's `contract.notes` may document whether it can be called in
"mesh-only" mode (e.g. via an env var). If yes, dispatch with the env
override. If no, **the task is "extend an existing E2E to expose a
mesh-only entry point"** (Step 4 path "基于现有宏改").

**(c) `case_family: multi` cross-cutting** — many utility macros
(`case_family: multi, phase: probe|mesh|solve|postprocess`) apply
across all 16 cases. The task may be solvable with a `multi` macro if
the intent is introspection / mesh / postprocess. Look for `multi`
matches before declaring "no match".

**(d) Different case_family but same intent** — e.g. the task is a
new `backward_facing_step` case but the only existing reference is
`lid_driven_cavity` (both internal flows, both k-omega SST). Decision:
**write from scratch** but cite the LDC macro as a template (Step 4
path "从零写").

### Step 4 — Decision: reuse / extend / write from scratch

This is the core dispatch decision. The decision matrix in §5 maps
the outcome of Steps 2-3 to one of three actions.

### Step 5 — Validate contract + pick dispatch mechanism

Once an entry is picked, read its `contract`:

- `input_kind` — confirm the agent has the right input (`.sim` path,
  STL, or "none")
- `output_kind` — confirm downstream code expects that output
- `parameters` / `env` — build the dispatch args
- `expected_outputs` — record what should appear in `Cases/Results/`
  after the run; downstream verification depends on these paths
- `approximate_wall_s` — feed into the harness timeout

Dispatch mechanism:

- **Stage 1+2 (stub adapter)**: the agent cannot call STAR-CCM+ for
  real. The dispatch is **simulated** — agent writes the `RunReport`
  that *would* result, marks it `executor_mode: MOCK` or
  `MODE_NOT_YET_IMPLEMENTED`. The registry is still consulted so the
  MOCK report reflects what a real run would do (parameters, expected
  outputs).
- **Stage 3+ (real adapter)**: agent calls
  `packages/starccm-bridge::run_macro(sim_path, macro_path, args, env)`
  per the contract. The bridge reads the macro path *from the
  registry* (or accepts it as a parameter, with the registry as the
  authoritative lookup layer).

### Step 6 — Run + verify

Execute per the contract. The verification gates (per the V&V engine)
are unchanged by this workflow — this doc only governs *which macro
gets called*, not *whether the result passes tolerance*.

### Step 7 — Update the registry (when warranted)

Three registry mutations are first-class outcomes of a dispatch:

1. **`reference → proven` bump.** If the task's run succeeded and
   the macro was previously `reference`, the agent (or the
   starccm-adapter-engineer) edits the registry:
   - `status: reference → proven`
   - `verified_by: <path to the new test/audit>`
   - `verified_at: <ISO-8601>`
2. **`reference → deprecated` mark.** If the run *failed* and the
   user ratifies a deprecation, set `status: deprecated` and
   `superseded_by` (or `notes:` if no successor yet).
3. **New entry.** If the agent wrote a new macro (Step 4 path
   "从零写"), it MUST be registered before the task's PR merges.
   Per the schema's §4.2 write policy, the agent adds the entry in
   alphabetical order, with `status: reference` (not `proven`
   until verified).

A new agent reading the registry after these mutations should see an
honest state — the most recent verified truth, not a backslide.

## 4. The `registry_lookup_record` (audit shape)

Every dispatch decision leaves a `registry_lookup_record` in the
task's `deliverable.md`. Schema:

```yaml
# In deliverable.md, as a fenced block:
registry_lookup_record:
  task_id: <DEC-XXX or task label>     # links to the decision trail
  case_id: naca0012_airfoil             # from TaskSpec
  case_family: naca0012_airfoil
  phase: full_pipeline
  intent: "Run NACA 2412 Re=6e6 AoA=2° within Ladson 1988 tolerance"
  search_performed:
    - step: 2_exact
      query: "case_family=naca0012_airfoil AND phase=full_pipeline"
      hits:
        - id: naca_2412_e2e_v1
          status: proven
          verified_by: reports/STATE.md
    - step: 3a_same_case_family_diff_phase
      query: "case_family=naca0012_airfoil AND phase!=full_pipeline"
      hits: []  # no other naca macros
    - step: 3d_cross_family_template
      query: "case_family in (lid_driven_cavity, multi) AND intent~'full_pipeline'"
      hits:
        - id: lid_driven_cavity_e2e   # template, not for direct reuse
  decision: reuse                      # one of: reuse | extend | write_new
  decision_rationale: |
    Exact match naca_2412_e2e_v1 with status: proven. No code change
    needed. The DEC-007 path is canonical; re-using it preserves the
    audit chain.
  chosen_entry: naca_2412_e2e_v1
  contract_check:
    input_kind: stl                    # TaskSpec provides STL
    output_kind: multiple
    parameters_used: {iters: 500, re: 6.0e6, aoa_deg: 2.0}
    env_used: []
    expected_outputs:
      - "Cases/Results/naca2412_summary.json"
  post_dispatch_mutation: null         # or a description of the registry change
  autonomy_level: L0                   # L0 / L1 / L2 — affects Step 5 enforcement
```

The record is **mandatory** at every dispatch. A deliverable.md
without it is a four-question-gate violation (the chief engineer
MUST reject the PR).

## 5. The decision matrix

Six concrete scenarios, mapped to the three actions.

| # | Scenario | Search outcome | Action | Rationale |
|---|---|---|---|---|
| 1 | **NACA 2412 full run on existing macro** | Step 2 (A) exact match `naca_2412_e2e_v1`, `status: proven` | **REUSE** | Proven path; no code change; preserves audit chain |
| 2 | **LDC Ghia 1982 tolerance check** | Step 2 (A) exact match `lid_driven_cavity_e2e`, `status: proven`; FF sampling issue noted in `notes:` | **REUSE** + flag the known issue | The macro is proven to *run*; the FF-sampling issue is independent of the macro choice and documented in the registry |
| 3 | **NACA 2412 with new AoA=12° (out of macro's tested range)** | Step 2 (A) exact match exists, but contract.parameters has no `aoa_deg: 12.0` config; macro was proven at AoA=5° only | **EXTEND** | Macro is the right shape; just add a new param branch + a new `tags: ["aoa-12"]`. Per write policy, bump `verified_by` after smoke |
| 4 | **Backward-facing step, full pipeline** (no `backward_facing_step` macro exists) | Step 2 (D) no exact match; Step 3 (d) cross-family template: `lid_driven_cavity_e2e` (same internal-flow SST shape) | **WRITE NEW** | Cite the LDC macro as template; new macro lives in `D:\CFD-harness-Windows-StarCCM\macros\BackstepE2E.java` (harness overlay); register with `status: reference` + add a `supersedes_status: false` lineage note for future migrations |
| 5 | **Vortex street force-history postprocess** | Step 2 (A) exact match `vortex_street_v14`, `status: proven` | **REUSE** | V14 has the V161R cylinder-region fix; do not regress to V12.5 (`vortex_street_spawn_root`) |
| 6 | **Patch an existing macro** (e.g. user reports `LidDrivenCavity.java` BC setter fails on a corner case) | Step 2 (A) exact match `lid_driven_cavity_e2e`, `status: proven`; but the macro has a real bug | **EXTEND** (the patch IS the new entry; the old entry stays, marked `supersedes_status: true` if a new `lid_driven_cavity_e2e_v2` replaces it). **OR** if the fix is small and on the harness overlay, just patch `LidDrivenCavity.java` in place and update the registry's `notes:` with the patch summary | Per `AGENTS.md` § "Crew directives" — never weaken gold standards' tolerance to make a benchmark pass; never silently switch executor. The patch goes through DEC review |

The matrix is not exhaustive. New scenarios map to the same three
actions by analogy: "does an existing macro *fit*?" → reuse;
"does one *almost* fit?" → extend; "is this a genuinely new
case_family / phase?" → write new.

## 6. Failure fallback — when the registry says "no match"

If Steps 2-3 produce zero actionable hits, the agent follows this
fallback chain before writing code:

1. **Widen the search** — re-read `knowledge/skill_index.yaml` for
   any LLM-skill cross-link; check `case_profiles.yaml:macros` for
   case-specific hints; check `D:\StarCCM Codebuddy\macros\` directly
   for any recent file the registry hasn't catalogued yet (the
   registry is hand-curated, ~1-week lag is normal per schema §5).
2. **Surface to the chief engineer** — in the `deliverable.md`,
   write a `registry_gap_record`:

   ```yaml
   registry_gap_record:
     case_id: <the case we couldn't find>
     case_family: <its case_family>
     phase: <its phase>
     intent: <what we wanted to do>
     search_performed:
       - step: 2_exact
         hits: []
       - step: 3a
         hits: []
       - step: 3c_multi
         hits: []
     fallback_decision: write_new   # or "blocked" if the user must decide first
     rationale: |
       Registry has no match. The closest is X (different case_family)
       so we treat this as a new entry. New macro will be added to
       D:\CFD-harness-Windows-StarCCM\macros\ as a harness overlay,
       registered as reference until proven.
   ```

3. **Register the gap for the next sweep** — the
   `docs-knowledge-engineer` owns the next-sweep backlog
   (`skipped_need_metadata` in the registry's footer). Adding a new
   gap entry to that backlog is the lowest-friction way to make the
   registry honest about its blind spots.
4. **Do NOT silently widen the `case_family` enum** — if the new
   case is genuinely outside `whitelist.yaml:all_cases`, the user
   must add the case to whitelist FIRST (per schema §3.5: "If a new
   case is added to `whitelist.yaml`, add it to the `case_family`
   enum here in the same commit."). This is a governance step, not
   an agent step.

## 7. Autonomy-level enforcement (L0 / L1 / L2)

The graduated autonomy ladder in `chief-engineer/agent.md` § "Graduated
autonomy ladder" applies to dispatch too:

| Level | Lookup requirement | Mutation requirement | Push rights |
|---|---|---|---|
| **L0 · Advisory** (current default) | REQUIRED before any code is written; chief engineer ratifies the decision before dispatch | `reference → proven` bumps: chief engineer signs off; `deprecated` marks: requires user ratification. New entries: chief engineer signs off | None — user authorizes each push |
| **L1 · Supervised** | REQUIRED; chief engineer may ratify silently if the lookup_record is complete and the decision matches the §5 matrix | `reference → proven` bumps may proceed without explicit sign-off; `deprecated` marks still require user | Push within-stage passing work |
| **L2 · Full autonomy** | REQUIRED; the record is the audit | All mutations autonomous; chief engineer reviews the audit log on the next cycle | Push validated work |

**L0 is non-negotiable**: the chief engineer CANNOT skip the lookup
even when it would obviously recommend `reuse`. The point of the
record is not just to find the right macro — it's to **prove** the
right macro was found, on the record, every time. L0 is a process
discipline, not a speed optimization.

## 8. Compatibility with project invariants

This workflow is designed to slot into the existing project
guarantees without modification:

- **Advisor-not-driver** (`AGENTS.md` § "Crew directives"): the
  registry is a *lookup* layer, not a *mutation route*. The product
  AI never reads the registry to decide what macro to run — the
  user / case_profiles drives. The registry is consulted by
  *agents* in the *dev process*. The chief engineer dispatches the
  work; the product runtime is unchanged.
- **Four-plane law** (`docs/adr/ADR-001-four-plane-import-enforcement.md`):
  the registry is a YAML, not a Python module. There are no
  cross-plane imports to violate. The downstream consumers
  (`starccm_adapter`, `case_profiles`) remain in their respective
  planes; this workflow just directs humans + LLMs to use the
  registry before touching the adapter.
- **Four-question gate** (`AGENTS.md`): the registry lookup does
  not affect the four questions. They are still asked at the PR /
  stage-boundary level. The registry just makes the "Clear artifacts"
  and "TrustGate explains trust" answers more concrete (the
  artifact is a real macro; the trust is `status: proven` + a
  linked test).
- **Mock-first** (`AGENTS.md` § "Five ground rules"): the registry
  is solver-agnostic in *spirit* (cataloging macros) but
  solver-specific in *content* (only STAR-CCM+ macros). The MOCK
  executor still works without it — the registry is purely advisory
  at runtime.

## 9. What this workflow explicitly does NOT do

To avoid scope creep and to keep the chief engineer / adapter
engineer prompts tight:

- **Does not replace the executor**. The executor still calls
  `run_macro(sim_path, macro_path, args, env)` per the contract.
  This workflow only changes *how the agent picks `macro_path`*.
- **Does not introduce a CLI dispatch tool**. Task A's deliverable
  explicitly says "yaml 浏览, 不写 CLI". This workflow operates
  with humans + LLMs reading the YAML directly. A future `cfd-harness
  run-macro <id>` CLI is a separate task (Task C in the plan).
- **Does not change case_profiles.yaml semantics**. The profile
  still says "this case uses these macros"; the registry still
  says "this macro does X". The two files cross-link at the
  `filename` field; chief engineer keeps them in sync.
- **Does not auto-populate the registry**. Per schema §4.1, the
  registry is hand-curated for v1. A v2 linter is a separate task.

## 10. Worked examples (canonical + edge cases)

### 10.1 Canonical reuse — LDC Ghia 1982

Task: "Compute lid-driven cavity Ghia 1982 centerline u-velocity,
Re=10000, mesh_40."

```yaml
registry_lookup_record:
  task_id: DEC-LDC-GHIA-RUN
  case_id: lid_driven_cavity
  case_family: lid_driven_cavity
  phase: full_pipeline
  intent: "Compute LDC u-centerline for Ghia 1982 validation, Re=10000, mesh_40"
  search_performed:
    - step: 2_exact
      query: "case_family=lid_driven_cavity AND phase=full_pipeline"
      hits:
        - id: lid_driven_cavity_e2e
          status: proven
          verified_by: packages/starccm-bridge/tests/test_lid_driven_cavity_e2e.py
  decision: reuse
  decision_rationale: |
    Exact match, status: proven. Mesh_40 maps to LDC_ITERS=500
    per executor:204 mapping. FF sampling for Ghia is BLOCKED on
    STAR-CCM+ 19.02.009 API (DEC-005); user will GUI-verify.
  chosen_entry: lid_driven_cavity_e2e
  contract_check:
    input_kind: stl
    output_kind: multiple
    parameters_used: {iters: 500}
    env_used: ["LDC_ITERS=500"]
    expected_outputs:
      - "Cases/Results/lid_driven_cavity_solved.sim"
      - "Cases/Results/lid_driven_cavity_summary.json"
      - "Cases/Results/lid_driven_cavity_u_centerline.csv"
  post_dispatch_mutation: null
  autonomy_level: L0
```

### 10.2 Edge: extend for new AoA

Task: "NACA 2412 at AoA=12° (macro was tested at AoA=5°)."

```yaml
registry_lookup_record:
  task_id: DEC-NACA-AOA12
  case_id: naca0012_airfoil
  case_family: naca0012_airfoil
  phase: full_pipeline
  intent: "NACA 2412 Re=6e6 AoA=12° for new benchmark"
  search_performed:
    - step: 2_exact
      query: "case_family=naca0012_airfoil AND phase=full_pipeline"
      hits:
        - id: naca_2412_e2e_v1
          status: proven
          notes: "AoA=5° only"
  decision: extend
  decision_rationale: |
    Macro shape is right; just add a 12° branch. New tag
    ["aoa-12"] in the registry, new test in
    tests/test_naca_aoa12_e2e.py. Will bump status to
    proven after smoke.
  chosen_entry: naca_2412_e2e_v1
  contract_check:
    input_kind: stl
    output_kind: multiple
    parameters_used: {re: 6.0e6, aoa_deg: 12.0, iters: 500}
    env_used: []
    expected_outputs: ["Cases/Results/naca2412_summary.json"]
  post_dispatch_mutation: |
    Patch NacaTrueE2E.java to accept aoa_deg=12.0; add
    "aoa-12" to tags; add tests/test_naca_aoa12_e2e.py;
    bump verified_by + verified_at after smoke.
  autonomy_level: L0
```

### 10.3 Edge: write new for new case family

Task: "Backward-facing step, Re=5000, full pipeline." (No BFS macro
in registry.)

```yaml
registry_lookup_record:
  task_id: DEC-BFS-NEW
  case_id: backward_facing_step
  case_family: backward_facing_step   # in whitelist
  phase: full_pipeline
  intent: "Backward-facing step, Re=5000, k-omega SST, full pipeline"
  search_performed:
    - step: 2_exact
      hits: []
    - step: 3a_same_family_diff_phase
      hits: []
    - step: 3d_cross_family_template
      hits:
        - id: lid_driven_cavity_e2e   # template, internal flow SST
  decision: write_new
  decision_rationale: |
    No match. The LDC macro is a useful template (same internal-flow
    SST shape), but the geometry + BC structure differs (step
    expansion vs. moving lid). New harness-overlay macro
    BackstepE2E.java, registered reference until proven.
  chosen_entry: null
  contract_check: null
  post_dispatch_mutation: |
    Create D:\CFD-harness-Windows-StarCCM\macros\BackstepE2E.java
    (harness overlay). Register at knowledge/macro_registry.yaml
    with id=backstep_e2e_v0, status=reference, case_family=
    backward_facing_step, phase=full_pipeline.
  autonomy_level: L0
```

## 11. Change log

- v1.0 (2026-06-11) — first cut. Companion to Task A's
  `macro_registry.yaml` + `MACRO_REGISTRY_SCHEMA.md`. Seven-step
  flow, four-decision matrix, autonomy-level enforcement, three
  worked examples. Awaiting user ratification.
