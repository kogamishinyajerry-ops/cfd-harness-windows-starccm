# cfd-harness-windows-starccm

> A multi-agent CFD V&V workbench for **Windows + STAR-CCM+ 2402**, adapted from
> [`cfd-harness-unified`](https://github.com/kogamishinyajerry-ops/cfd-harness-unified)
> (originally macOS + OpenFOAM + Docker).

This repo **inherits the architecture and V&V engine** of cfd-harness-unified and
**replaces the OpenFOAM adapter layer** with a Windows-native STAR-CCM+ bridge
that calls your existing [`D:\StarCCM Codebuddy`](../../D:/StarCCM%20Codebuddy)
CLI (1686 tests) over its REPL — no re-implementation of your solver tooling.

## Status (2026-06-09)

| Stage | Scope | Status |
|---|---|---|
| Stage 0 | Reconnaissance + planning | done |
| Stage 1 | Scaffold: reins + AGENTS.md + executor base/mock + 17 gold_standards + stub adapter | in progress |
| Stage 2 | V&V engine port (auto_verifier / report_engine / audit_package / metrics) + 150 tests | pending |
| Stage 3 | Real STAR-CCM+ bridge: 1 case (LDC) E2E | not started |
| Stage 4 | 3 anchor cases (LDC + NACA + cylinder wake) end-to-end | not started |

## Quick start (after Stage 2 lands)

```bash
# Python 3.12 is the supported runtime
python3.12 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest tests/ -q                       # all green on MOCK executor
.venv/bin/python -m cfd_harness.cli run --case lid_driven_cavity --executor mock
```

## Architecture (one screen)

```
.agents/skills/                 # OpenCode skills (mavis)
.harness/reins/                 # multi-agent reins (OpenCode 协议)
        chief-engineer/         # apex delivery owner
        starccm-adapter-engineer/
        vv-director/
        system-architect/
        backend-engineer/
        test-red-team/
        docs-knowledge-engineer/

knowledge/                      # solver-agnostic
        gold_standards/*.yaml   # 17 cases — literature-anchored V&V benchmarks
        whitelist.yaml          # canonical case list
        attestor_thresholds.yaml
        skill_index.yaml
        schemas/                # Pydantic / TypedDict contract shapes

src/
        executor/               # ExecutorMode: MOCK · DOCKER_OPENFOAM · WIN_STARCCM
        auto_verifier/          # convergence, gold_standard_comparator, physics_checker
        report_engine/          # data_collector, generator, contract_dashboard
        audit_package/          # signed manifest for V&V audit trail
        metrics/                # V&V metrics
        orchestrator/           # skill_loader (solver-agnostic dispatcher)
        starccm_adapter/        # STAR-CCM+ specific bridge (Stage 3+)

packages/
        starccm-bridge/         # subprocess → D:\StarCCM Codebuddy REPL

docs/
        specs/                  # EXECUTOR_ABSTRACTION.md (port v0.2)
        adr/                    # four-plane law (port from cfd-harness-unified)
        design/ · gates/ · methodology/ · scope/ · specs/
        starccm_corpus/         # (replaces openfoam_corpus/)

tests/                          # 150 mock-first tests + 56 fixtures (8 cases × 7 mesh densities)
```

## Five ground rules (carried over from cfd-harness-unified)

1. **Mock-first** — `ExecutorMode.MOCK` always works without STAR-CCM+ installed.
   Real executor is opt-in.
2. **V&V loop is solver-agnostic** — gold standards cite Ghia 1982 / Ladson 1988
   / Williamson 1996 (literature); only the `solver_info` block changes between
   OpenFOAM and STAR-CCM+.
3. **Multi-agent chief engineer pattern** — `chief-engineer` owns delivery;
   `vv-director` and `system-architect` are on-demand consults; never let a
   product-runtime AI mutate a case.
4. **Byte-deterministic signed audit package** — every benchmark run gets a
   SHA-256 over `(spec_hash | executor_mode | executor_version)`.
5. **Tolerance integrity is non-negotiable** — never weaken a tolerance to
   make a benchmark pass; if the benchmark fails, fix the pipeline, not the gate.

## See also

- `AGENTS.md` — OpenCode agent protocol entry (replaces `CLAUDE.md` and
  `.claude/agents/` of the original).
- `docs/specs/EXECUTOR_ABSTRACTION.md` — ported v0.2 spec; the 4-mode contract.
- `docs/adr/` — four-plane import/runtime law.
- `knowledge/gold_standards/` — 17 literature-anchored V&V benchmarks.
- `reports/STATE.md` — current delivery state (SSOT for progress).
