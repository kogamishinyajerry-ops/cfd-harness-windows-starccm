# OpenCode / Mavis memory and skill pointers

This file is a stub for OpenCode / Mavis runtime config.

The actual multi-agent reins live under `.harness/reins/` (one directory
per rein, each with an `agent.md` prompt file — see `AGENTS.md` for the
full crew architecture).

## Project-level state (SSOT)

- Delivery state: `reports/STATE.md`
- Decisions: `reports/decisions/`
- Plans / blueprints: `reports/blueprints/`
- Codex / review reports: `reports/codex/`
- V&V audit reports: `reports/audit/`

## Conventions

- `Mavis` mavis = Mavis / OpenCode's Mavis protocol
- `reins/` = Mavis's multi-agent reins (replaces Claude Code's
  `.claude/agents/` convention)
- `cfd-harness-windows-starccm` is the canonical project name
- Python package: `cfd_harness` (importable as `cfd_harness.auto_verifier` etc.)

## Why this repo exists

- Original: [`kogamishinyajerry-ops/cfd-harness-unified`](https://github.com/kogamishinyajerry-ops/cfd-harness-unified)
  (macOS + OpenFOAM + Docker, with a full V&V engine and 10-agent crew)
- Target: Windows + STAR-CCM+ 2402, with a Codebuddy REPL bridge
- Inherited: multi-agent architecture, V&V engine, 17 gold standards, four-plane law
- Rewritten: solver adapter (OpenFOAM → STAR-CCM+), UI deferred, executor modes
  extended with `WIN_STARCCM`
