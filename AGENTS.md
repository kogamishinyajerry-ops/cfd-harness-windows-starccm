# cfd-harness-windows-starccm · Project AGENTS.md

> Project-specific OpenCode / Mavis configuration. Inherits from
> `~/.mavis/AGENTS.md` (user-level).
>
> **Adapted from cfd-harness-unified** (kogamishinyajerry-ops/cfd-harness-unified),
> which targeted macOS + OpenFOAM + Docker. This repo retargets the same
> multi-agent architecture + V&V engine to **Windows + STAR-CCM+ 2402** via
> the existing `D:\StarCCM Codebuddy` CLI (1686 tests) as a bridge.

---

## Crew architecture (v2.3 · 2026-06-09)

This project uses a multi-agent crew coordinated by the **chief-engineer**
(apex delivery owner). The crew replaces cfd-harness-unified's
`.claude/agents/` Claude-Code-native pattern with OpenCode's
`.harness/reins/` convention — same role semantics, portable agent prompts.

| Tier | Rein / agent | Status | Owns |
|---|---|---|---|
| **Sponsor / final authority** | the human user | live | direction, charter ratification, autonomy grants |
| **Apex delivery-owner** | **`chief-engineer`** (`.harness/reins/chief-engineer/`) | **live** | drives the v1 delivery arc (Stage 1→4); coordinates the crew; wired to `.planning/STATE.md` |
| **Implementation** | `backend-engineer`, `starccm-adapter-engineer`, `docs-knowledge-engineer` | usable | mechanical impl dispatched by the chief engineer; chief reviews diffs |
| **Domain consults (on-demand)** | `vv-director` (V&V / tolerance / "covered" semantics), `system-architect` (boundaries / four-plane law / schemas) | **live (repointed)** | consulted by the chief engineer at exit gates / boundary-touching changes; NOT autonomous owners |
| **Audit / QA** | `test-red-team` | usable | independent functional/audit tests commissioned at exit gates |
| **Implementation** (also) | `docs-knowledge-engineer` | usable | corpus / docs / knowledge work |
| **External AI relay** | (OpenCode GLM-5.1, already deployed in user's intranet) | live | primary LLM; same role as Codex relay in the original |
| **Bridge (infrastructure)** | `D:\StarCCM Codebuddy` REPL | live | STAR-CCM+ CLI + 1686 tests; invoked via `packages/starccm-bridge/` |

**Honest state of the crew at v1 bootstrap (2026-06-09)**: the **chief-engineer
+ starccm-adapter-engineer + vv-director + system-architect + backend-engineer +
test-red-team + docs-knowledge-engineer** reins are the active crew. Marketing
and frontend-engineer are deferred (the v1 deliverable is **headless** —
CLI/agent-driven; UI is Stage 5+).

The original repo's "kogami strategic layer" (Claude-Code-specific) is **not
ported** — it relied on the `claude -p` subprocess, which is not available in
the user's OpenCode + GLM-5.1 environment. The strategic-review function is
replaced by user ratification on every phase boundary (chief-engineer L0 mode).

## Graduated autonomy (default L0)

- **L0 · Advisory** (current): chief engineer drives inside a user-approved
  phase; stops at every phase boundary; no autonomous push.
- **L1 · Supervised**: executes + pushes passing work within a phase; stops at
  exit gates for the next-phase go/no-go.
- **L2 · Full autonomy** (post-maturity): drives multi-phase, makes exit-gate
  calls, pushes validated work; only charter/direction changes return to user.

Graduation is **evidence-gated** (zero gate-violations, exit-gate calls
confirmed correct by evidence, V&V loop closed), not calendar-gated.

## Five ground rules (carried over verbatim from cfd-harness-unified)

1. **Mock-first** — `ExecutorMode.MOCK` always works without STAR-CCM+ installed.
2. **V&V loop is solver-agnostic** — gold standards cite literature; only the
   `solver_info` block differs across OpenFOAM and STAR-CCM+.
3. **Multi-agent chief engineer pattern** — chief engineer owns delivery;
   vv-director and system-architect are on-demand consults.
4. **Byte-deterministic signed audit package** — SHA-256 over
   `(spec_hash | executor_mode | executor_version)`.
5. **Tolerance integrity is non-negotiable** — never weaken a tolerance to
   make a benchmark pass.

## The four-question gate

Before any phase-complete / exit-gate-passed claim, the chief engineer
applies the four-question gate to its work:

1. LLM-offline runnable? (does it work without an LLM call?)
2. Clear artifacts? (does it produce a benchmark run + quantified error vs gold?)
3. TrustGate/completeness/audit explains trust? (is the verdict traceable?)
4. AI advisory-only, no mutating route? (does the product AI never mutate a case?)

Any "no" → redesign. This is the project's load-bearing invariant.

## Pre-implementation discipline

Before starting any non-trivial implementation work — **≥30 LOC OR new
top-level file** — run a 2-step pre-implementation surface scan:

1. **ROADMAP scan** — read `reports/STATE.md` §current-phase, identify
   whether the proposed feature maps to a known item.
2. **Existing-implementation grep** — `grep -rin "<feature_keyword>"` over
   `src/`, `tests/`, `packages/`, `docs/`; read first 60 lines of any matched
   file. If a substantial pre-existing implementation is found, STOP and
   surface to user with disposition options (a) extend / (b) parallel new /
   (c) refactor.

Skip clauses: routine bugfix on already-located file · CLASS-1 docs-only ·
user explicitly says "rewrite X" · trivial single-file edit ≤10 LOC AND no
new top-level file. Trigger wins on conflict.

## Surface mapping from cfd-harness-unified

| Original (macOS + OpenFOAM) | This repo (Windows + STAR-CCM+) | Notes |
|---|---|---|
| `.claude/agents/*.md` (10 agents) | `.harness/reins/*/agent.md` (7 agents) | v1 active crew; kogami + marketing + frontend retired |
| `src/foam_agent_adapter.py` (440KB) | `src/starccm_adapter/` (Stage 3+) | thin bridge via Codebuddy REPL |
| `src/executor/docker_openfoam.py` | `src/executor/win_starccm.py` (Stage 3+) | local STAR-CCM+ install (not Docker) |
| `src/meshing_gmsh/ + meshing_snappy/` | not ported | STAR-CCM+ does its own meshing via Java macros |
| `ui/backend/services/case_solve/` | `src/starccm_adapter/case_solve/` (Stage 3+) | rewrite using Codebuddy REPL commands |
| `ui/backend/services/case_extractors/` | `src/starccm_adapter/case_extractors/` (Stage 3+) | rewrite to read STAR-CCM+ field data |
| `ui/backend/services/case_visualize/` | `src/starccm_adapter/case_visualize/` (Stage 3+) | rewrite using STAR-CCM+ scene + export |
| `ui/backend/services/mesh_quality/` | `src/starccm_adapter/mesh_quality/` (Stage 3+) | STAR-CCM+ mesh report parser |
| `ui/backend/services/physics/` | `src/starccm_adapter/physics/` (Stage 3+) | materials + regimes + tolerance binding |
| `ui/` (FastAPI + React) | deferred to Stage 5+ | v1 is headless / agent-driven |
| `src/auto_verifier/` | ported verbatim | solver-agnostic |
| `src/report_engine/` | ported verbatim | solver-agnostic |
| `src/audit_package/` | ported verbatim | solver-agnostic |
| `src/metrics/` | ported verbatim | solver-agnostic |
| `src/orchestrator/skill_loader.py` | ported verbatim | solver-agnostic |
| `src/executor/{base,mock}.py` | ported verbatim | solver-agnostic |
| `knowledge/gold_standards/*.yaml` | ported with `solver_info` retargeted to STAR-CCM+ | reference values (Ghia, Ladson, etc.) unchanged |
| `knowledge/{whitelist,attestor_thresholds,skill_index,schemas}` | ported verbatim | solver-agnostic |
| `docs/specs/EXECUTOR_ABSTRACTION.md` | ported v0.2 (with `WIN_STARCCM` mode added) | executor contract |
| `docs/adr/` | ported verbatim | four-plane law (solver-agnostic) |
| `.planning/decisions/` (431 DECs) | **not ported** | fresh `.planning/STATE.md` starts empty |

## Inherited user-level rules

`~/.mavis/AGENTS.md` governs (v2.3 baseline):
- Subagent 优先原则 (push to subagent when main context ≥35% consumed)
- DEC scope-driven (charter / cross-module / governance-rule-change → full DEC)
- 1M ctx 校准
- Cadence floor THRESHOLD 30
- Surface-scan trailer (above) encouraged

## Crew directives (analogous to cfd-harness-unified's "Forbidden actions")

The chief engineer and every other rein MUST NOT:

- Let STAR-CCM+-specific code leak outside `src/starccm_adapter/`,
  `packages/starccm-bridge/`, or `src/executor/win_starccm.py` (the adapter
  boundary — per `docs/adr/ADR-001-four-plane-import-enforcement.md`).
- Switch the executor from `MOCK` to `WIN_STARCCM` silently — must be opt-in
  flag (`--executor win_starccm` or `STARCCM_EXECUTOR=enabled`).
- Claim `validation_status: validated` from inside the adapter.
- Modify gold standards' `reference_values` to make a benchmark pass.
- Weaken a `tolerance` field in `knowledge/gold_standards/*.yaml` without a
  documented evidence trail in `reports/`.

## Imports & package layout

This project uses the `src/` layout (PEP 660 editable install):

```
src/
  cfd_harness/
    __init__.py
    auto_verifier/        # V&V engine
    report_engine/        # V&V engine
    audit_package/        # signed audit trail
    metrics/              # V&V metrics
    orchestrator/         # skill_loader
    executor/             # MOCK · DOCKER_OPENFOAM · WIN_STARCCM
    starccm_adapter/      # STAR-CCM+ bridge (Stage 3+)
    models/               # TaskSpec, ExecutionResult, FlowType, etc.
  packages/
    starccm-bridge/       # subprocess → Codebuddy REPL
```

The Python package name is `cfd_harness` (not `src`); import as
`from cfd_harness.auto_verifier import ...`. This differs from the
original which used `from src.auto_verifier import ...` (top-level
`src` package) — the rename keeps the import path clean and avoids
clashes with the stdlib `src` keyword usage.

## Required files to read before acting (the live system)

- `AGENTS.md` (this file) + `~/.mavis/AGENTS.md`
- `reports/STATE.md` (current delivery state — SSOT for progress)
- `docs/specs/EXECUTOR_ABSTRACTION.md` (the 4-mode contract)
- `docs/adr/ADR-001-four-plane-import-enforcement.md` (the four-plane law)
- `knowledge/whitelist.yaml` (canonical case list)
- The actual code under review

## Definition of success

- Every "covered" claim in `reports/STATE.md` is backed by a benchmark that
  passed its tolerance gate end-to-end through the executor.
- The V&V loop (gold → run → compare → verdict) is a single visible flow
  for ≥1 vertical on the WIN_STARCCM executor.
- Crew division of labor is legible: anyone reading `AGENTS.md` knows who
  owns what and how the chief engineer coordinates them.
