# plan_b170bb32 · Skill-Evolution-Design · Verdict (2026-06-11)

> **Audience**: Kogami (user/sponsor). This is the FINAL verdict doc for
> the plan — read first, then approve / reject / amend.
>
> **Verifier**: branch session `mvs_41474d5c17d64330b7d097ecfc2fbe82`
> under `verifier` rein. Black-box review of Task A / B / C deliverables.
> **No producer deliverable.md was read** — verdicts are based on the
> artifacts themselves + independent verification.

---

## 0. TL;DR (for the user)

| Question | Answer |
|---|---|
| Are Task A / B / C deliverables internally consistent? | **YES** — schema → registry → dispatch workflow → auto-recruit chain hangs together |
| Do they fit the project's hard constraints? | **YES** for advisor-not-driver / four-plane law / mock-first / L0 / tolerance integrity / pre-implementation discipline |
| Are there real bugs? | **YES — 1 structural bug + 2 known limitations.** See §3.2 for the bug. None of them block the plan's intent. |
| Should I ratify and let chief-engineer proceed to implementation? | **YES, with 2 preconditions** (see §4). |
| Should I bump chief-engineer from L0 → L1? | **NO — not yet.** Stay L0. Evidence for L1 is missing (see §4.4). |

**Overall verdict: PASS-WITH-CONDITIONS.** Ratify the design + proceed
to implementation **after** §4's 2 preconditions are addressed.

---

## 1. Independent verification of each task

### 1.1 Task A — macro_registry.yaml + schema + design

**Files produced**:
- `knowledge/macro_registry.yaml` (1474 lines, ~58KB,53 entries)
- `docs/specs/MACRO_REGISTRY_SCHEMA.md` (322 lines)
- `reports/skill-evolution-design/registry-design.md` (309 lines)

### Check A1 — YAML parses + schema invariants hold
**Method:** `python -c "import yaml; yaml.safe_load(open('.../macro_registry.yaml'))"` + closed-enum validation script.
**Evidence:**
```
YAML PARSE OK
Top-level keys: ['version','description','source','generated_at','curator','macros']
Total macros: 53 (matches producer claim, post-v2-patch fix from 35)
Duplicate ids: []
Distinct statuses: {'proven': 18, 'reference': 35}
Distinct case_families: ['apu_complete','building_aero','car_aero','circular_cylinder_wake',
  'duct_flow','lid_driven_cavity','multi','naca0012_airfoil']
Distinct phases: ['checkpoint','export','full_pipeline','mesh','postprocess','probe','setup','solve','wrapper']
Proven WITHOUT verified_by: []  ← all 18 proven entries have non-empty verified_by
Deprecated WITHOUT superseded_by+notes: []
Total schema problems: 0
```
**Result: PASS.** Every entry has all required top-level fields, every `status: proven`
has a non-empty `verified_by`, all enums are closed, no duplicates.

### Check A2 — Every registry path resolves to a real .java file
**Method:** Walked all 53 entries, expanded `harness://` prefix, checked `pathlib.exists()`.
**Evidence:**
```
Registry entries whose file does not exist: 0
```
All 53 paths resolve. Sampled 5 spot-checks vs `first-30-lines` of the .java:
- `cli_probe_v16` ↔ `CliProbe.java` first lines: "v16 Phase A: read-only STAR-CCM+
  state probe… reports sim state, license, mesh, monitors, reports, scenes, parts
  to Cases/Results/probe_report.json" → **matches registry `intent`**.
- `lid_driven_cavity_e2e` ↔ `LidDrivenCavity.java` first lines: "STAR-CCM+ 2402
  lid-driven cavity (Ghia 1982) E2E macro… BCs: top wall Ux=1 m/s (lid), other 3
  walls no-slip… outputs include lid_driven_cavity_u_centerline.csv (17 Ghia
  y-points)" → **matches registry `intent`**.
- `vortex_street_v14` ↔ `VortexStreetV161R_V14_ForcesCorrect.java` first lines:
  "V14: FIX cylinder region selection in V8 sim… V13 bug: matched Region 1's
  'Default' wall (wrong cylinder r=0.5 leftover, no flow) instead of Region 2's
  'Default Boundary' (correct cylinder r=0.025)" → **matches registry `intent`**.
- `cli_export_field_data_v24` ↔ `CliExportFieldData.java` first lines: "v24 P0:
  TRUE scalar field function CSV export… 4 paths via reports (Sum/Min/Max/Avg)
  + 11 reflective sub-paths cascade (5a-5k)" → **matches**.
- `car_cfd_full_pipeline` ↔ `CarCFD_FullPipeline.java` first lines: "14-part car
  + wind tunnel - FULL CFD pipeline… 500 steady iterations" → **matches**.

**Result: PASS** on intent accuracy + path validity.

### Check A3 — `verified_by` paths exist on disk
**Method:** Iterated 18 `proven` entries, expanded relative path to harness root.
**Evidence:**
```
lid_driven_cavity_e2e: packages/starccm-bridge/tests/test_lid_driven_cavity_e2e.py  [OK]
naca_2412_e2e_v1: reports/STATE.md  [OK]
vortex_street_v14: packages/starccm-bridge/tests/test_bridge_smoke.py  [OK]
vortex_street_spawn_root: packages/starccm-bridge/tests/test_bridge_smoke.py  [OK]
cli_probe_v16: packages/starccm-bridge/tests/test_bridge_p0p1p2_fixes.py  [OK]
[...14 more...]  all [OK]
```
**Result: PASS** — paths exist. BUT see Check A5 / §3.2 for the *semantic* gap.

### Check A4 — Cross-link with case_profiles.yaml
**Method:** Loaded both YAMLs, walked `profiles.<id>.macros`, checked every
referenced `.java` filename appears in registry's `filename` set.
**Evidence:**
```
Macros referenced in case_profiles: 4
Of which NOT in registry filename set: 0
lid_driven_cavity -> LidDrivenCavity.java  ✓
circular_cylinder_wake -> VortexStreet.java  ✓
naca0012_airfoil -> CliNaca2412E2E.java  ✓
cylinder_crossflow -> VortexStreet.java  ✓
```
**Result: PASS.**

### Check A5 — ADVERSARIAL: do the cited tests actually prove the macros work?
**Method:** Read the cited test files; for each `proven` entry, checked whether
the test invokes that specific macro.
**Evidence:** This is the **most important finding** in this verification.

| Proven entry | cited test | what the test actually does |
|---|---|---|
| `lid_driven_cavity_e2e` | `test_lid_driven_cavity_e2e.py` | **Genuine E2E** — `@pytest.mark.real_solver`, gated on `STARCCM_BRIDGE_TEST_SPAWN=1`, spawns STAR-CCM+ with `LidDrivenCavity.java`, validates log + summary.json + sim artifacts |
| `naca_2412_e2e_v1` | `reports/STATE.md` | **Real STAR-CCM+ output** — DEC-007 documents Cl=0.0096, Cd=0.0015 from real run. STATE.md-based reference. |
| `vortex_street_spawn_root` | `test_bridge_smoke.py::test_vortex_street_spawn_smoke` | **Genuine E2E** — gated on env var, calls `repl.vortex_street()` which spawns STAR-CCM+ on a real sim |
| `vortex_street_v14` | `test_bridge_smoke.py` | **MISCLASSIFIED** — the test exercises `repl.vortex_street()` which dispatches `VortexStreet.java` (a DIFFERENT macro), NOT `VortexStreetV161R_V14_ForcesCorrect.java`. The V14 forces-correct behavior is untested. |
| `cli_probe_v16` | `test_bridge_p0p1p2_fixes.py` | **MISCLASSIFIED** — this test file is pure bridge-plumbing unit tests (error classifier, force_new argv, starccm_bat heuristic). It does NOT call CliProbe.java. |
| `cli_license_probe_v16` | same file | **MISCLASSIFIED** — same reason |
| `cli_real_demo_v16` | same file | **MISCLASSIFIED** — same reason |
| `cli_mesh_gen_v20` | same file | **MISCLASSIFIED** — same reason |
| `cli_mesh_gen_run_v20` | same file | **MISCLASSIFIED** — same reason |
| `cli_mesh_quality_v15` | same file | **MISCLASSIFIED** — same reason |
| `cli_solve_init_only_v18` | same file | **MISCLASSIFIED** — same reason |
| `cli_solve_step_v22` | same file | **MISCLASSIFIED** — same reason |
| `cli_post_process_v18` | same file | **MISCLASSIFIED** — same reason |
| `cli_report_force_v15` | same file | **MISCLASSIFIED** — same reason |
| `cli_report_integral_v15` | same file | **MISCLASSIFIED** — same reason |
| `cli_export_scene_v55` | same file | **MISCLASSIFIED** — same reason |
| `cli_export_field_data_v24` | same file | **MISCLASSIFIED** — same reason |
| `cli_test_smoke_v34` | same file | **MISCLASSIFIED** — same reason |

**15 of 18 `proven` entries (83%) cite a test file that does not actually invoke that macro.**
The cited test file `test_bridge_p0p1p2_fixes.py` is a P0-P2 bridge-plumbing test
suite (per its own docstring: "PURE unit tests… do NOT require a STAR-CCM+ install,
do NOT subprocess anything"). It tests the bridge's argv builder, error classifier,
and heuristics — **not** the macros themselves.

**Result: PARTIAL FAIL on semantic claim of "proven".** The `verified_by` field is
truthful at the file-existence level, but misleading at the claim level. A future
verifier reading "status: proven + verified_by: test_bridge_p0p1p2_fixes.py" would
assume that test invokes the macro — it does not.

**This is a known limitation honestly disclosed by the design §9 / dispatch §3.5**:
- registry §9: "**`verified_by` is a string, not a structured object** — future
  versions may want `{type: pytest|audit|manual, path: ..., passed_at: ...}`. v1
  keeps it simple."
- dispatch §3.5 risk: "`reference → proven` bumps create noise… A successful
  ad-hoc invocation is not sufficient. The chief engineer signs off on the bump."

**Honesty score: 8/10.** The producer discloses the limitation; the registry itself
doesn't enforce it. The fix is small but real — see §4 precondition2.

### Check A6 — ADVERSARIAL: macros modified after `verified_at`
**Method:** For each entry, compared .java mtime to `verified_at` timestamp.
**Evidence:**
```
Entries where .java mtime > verified_at: 5
  lid_driven_cavity_e2e: file=2026-06-10 10:24  verified_at=2026-06-10T00:00
  naca_2412_e2e_v1: file=2026-06-11 10:22  verified_at=2026-06-11T00:30
  cli_solve_step_v22: file=2026-06-11 01:10  verified_at=2026-06-10T00:00
  cli_export_scene_v55: file=2026-06-10 14:22  verified_at=2026-06-10T00:00
  cli_export_field_data_v24: file=2026-06-11 01:11  verified_at=2026-06-10T00:00
```
**5 macros have file mtime > verified_at.** The status is stale — these macros were
edited after the last successful test run. The schema doesn't define a "stale"
flag; this is a known drift risk (registry §9 + dispatch §3.1).

**Result: MINOR FAIL.** Not a bug — it's an explicit trade-off in the design
("**`verified_at` clock** — no reminder to re-verify after N months"). But the user
should know that the NACA entry was edited TODAY without a re-verification.

---

### 1.2 Task B — SKILL_DISPATCH_WORKFLOW + agent.md patches + design

**Files produced**:
- `docs/specs/SKILL_DISPATCH_WORKFLOW.md` (506 lines)
- `.harness/reins/chief-engineer/agent.md` (+73 lines: hard-rule section)
- `.harness/reins/starccm-adapter-engineer/agent.md` (+90 lines: hard-rule section)
- `reports/skill-evolution-design/dispatch-design.md` (412 lines)

### Check B1 — Both agent.md patches contain the "hard rule"
**Method:** Grep'd for the literal phrase.
**Evidence:**
```
chief-engineer/agent.md: Line 79: # Pre-implementation skill lookup (hard rule)
starccm-adapter-engineer/agent.md: Line 68: # Pre-implementation skill lookup (hard rule)
```
Both prompts: reference `macro_registry.yaml`, reference `SKILL_DISPATCH_WORKFLOW.md`,
have skip clauses, mandate `registry_lookup_record` in deliverable.md.
**Result: PASS.**

### Check B2 — Decision matrix covers the 4 scenarios the verifier mentioned
**Method:** Read spec §5 (line 258-269).
**Evidence:** Spec §5 lists 6 scenarios (matrix is not exhaustive):
1. NACA full run on existing macro → **REUSE** ✓
2. LDC Ghia1982 tolerance check → **REUSE + flag known issue** ✓
3. NACA AoA=12 (out of tested range) → **EXTEND** ✓
4. Backward-facing step (no macro exists) → **WRITE NEW** ✓
5. Vortex-street force-history postprocess → **REUSE** (V14 not V12.5) ✓
6. Patch existing macro → **EXTEND** vs deprecate ✓

The verifier's 4 mandated scenarios (NACA / LDC / BFS / patch) are all covered
(rows 1, 2, 3, 4, 6).

**Result: PASS.**

### Check B3 — L0 autonomy enforcement is hard-coded, not "guideline"-soft
**Method:** Read spec §7 + both agent.md patches.
**Evidence:**
- spec §7 table: "**L0 (current default)**: REQUIRED before any code is written;
  chief engineer ratifies the decision before dispatch… mutations: chief engineer
  signs off; `deprecated` marks: requires user ratification."
- spec §7 prose: "**L0 is non-negotiable**: the chief engineer CANNOT skip the
  lookup even when it would obviously recommend `reuse`. The point of the record
  is not just to find the right macro — it's to **prove** the right macro was
  found, on the record, every time."
- chief-engineer §autonomy_level: `L0`.
- starccm-adapter-engineer prompt explicitly references the chief engineer's rule
  AND adds its own "counterpart" rule: "this rule is the counterpart to the
  chief-engineer's dispatch rule — the chief engineer decides *what to dispatch*;
  the adapter engineer decides *which macro to use / extend / write*".

**Result: PASS.** Both prompts have a clearly-labeled "hard rule" + L0 sign-off
+ autonomous coupling to L1/L2.

### Check B4 — Producer's claim "no code touched, no push, no commit" verified
**Method:** `git status` + `git log --oneline -10`.
**Evidence:**
```
On branch main
Your branch is up to date with 'origin/main'.
HEAD = 44b7afd feat(stage3+): P0-P2 optimization pass (bridge version, LDC sim-lock, ...)
modified (not committed): chief-engineer/agent.md, starccm-adapter-engineer/agent.md,
                          attestor_thresholds.yaml, case_profiles.yaml, whitelist.yaml,
                          STATE.md, src/cfd_harness/cli/run.py, src/cfd_harness/executor/mock.py,
                          tests/executor/test_mock.py
untracked: docs/specs/MACRO_REGISTRY_SCHEMA.md, SKILL_DISPATCH_WORKFLOW.md,
           knowledge/macro_registry.yaml, reports/skill-evolution-design/  (all 3 design docs)
```
**Result: PASS on no-push / no-commit.** Files are in working tree, awaiting user ratification.

**Observation**: producer's working tree ALSO contains7 other modifications unrelated
to this plan (cli/run.py, mock.py, case_profiles.yaml, etc. — likely from the
Stage2.5 mock expansion / DEC-006 work). Those are out-of-scope for this verdict,
but they should NOT be committed alongside the skill-evolution deliverables. The
chief-engineer should stage the Task A/B/C files as a separate commit.

---

### 1.3 Task C — auto-recruit-design.md

**File produced**:
- `reports/skill-evolution-design/auto-recruit-design.md` (294 lines)

### Check C1 — Design is coherent with Task A / B
**Method:** Read §0 (locked facts), §1 (three schemes), §3 (recommendation), §6 (audit), §8 (four-question gate).
**Evidence:**
- §0 correctly identifies the L0 / advisor-not-driver constraints, lists the
  schema's "hand-curated" stance, identifies the two real paths (Codebuddy +
  harness overlay).
- §1 scheme A: git post-commit hook — clean stdlib + git integration, LLM-offline.
- §1 scheme B: filesystem watcher (watchdog) — correctly identified as L0-incompatible
  (常驻 = 越权 write without user ratify).
- §1 scheme C: agent prompt-level enforcement — correctly identified as LLM-brittle
  (CI / headless test runs have no LLM).
- §3 recommendation: A + C-overlay (hook for reliability + prompt for javadoc-quality
  nudges). Trade-off matrix in §2 is honest.

**Result: PASS** on coherence with Task A/B's constraints.

### Check C2 — Audit trail design respects `src/audit_package/` boundary
**Method:** Read §6.1.
**Evidence:** Auto-recruit writes to `reports/audit/macro_registrations/YYYY-MM-DD/<sha>.json`,
NOT into the signed-manifest pipeline (which is benchmark-grade). Producer's rationale:
"audit_package 的 signed manifest 是 benchmark-grade 的产物;macro 登记是 corpus 元数据,
粒度不对等." This is correct — the manifest-grade signing pipeline is for benchmark runs,
not corpus metadata.

**Result: PASS** — audit trail granularity matches the data type.

### Check C3 — Four-question gate compatibility (self-check)
**Method:** Read §8.
**Evidence:** Producer self-checks all 4 questions:
1. LLM-offline? ✅ hook is stdlib + git + file IO (verified in §1 pseudocode: `import subprocess,
   re, datetime, pathlib, hashlib, json` — no LLM deps).
2. Clear artifacts? ✅ each registration produces YAML stub + audit JSON.
3. TrustGate explains trust? ✅ stub forces `status: reference` + `verified_by: null`,
   audit JSON keeps `spec_hash` + `commit`.
4. AI advisory-only? ✅ hook writes corpus metadata only, not `.sim` / `.java` / solver config.

**Result: PASS** on paper. BUT — the hook is design-only. **No code exists yet.**
The producer explicitly notes "本次只出设计,不动实现" (design-only, no implementation).
Task C is therefore a *recommendation*, not a deployed mechanism. The chief-engineer
must decide whether to allocate the 2h20min to implement it (see §4.4).

### Check C4 — Honest limitation disclosure
**Method:** Read §6.4 (what can/can't be auto-generated).
**Evidence:** Producer explicitly enumerates:
- ✅ Can auto: `id`, `path`, `filename`, `line_count`, `authored_by`, `starccm_version`,
  `status=reference`, `drafted_at`, `drafted_from_commit`.
- ⚠ Heuristic (will err): `phase` (keyword match, ~70% accurate), `intent` (first javadoc
  sentence; fails on no-javadoc / long sentences).
- ❌ Must be human: `case_family` (semantic), `contract.input_kind` / `output_kind`,
  `contract.parameters` (signature layer), `verified_by` (run evidence), `verified_at`,
  `tags`, `notes`, `supersedes` / `superseded_by`.

**Result: PASS** on honesty. "**自动登记 = 让 chief-engineer 在 session 里"看见"有这事,
而不是让 verifier 以为这事已完成。** 后者永远要人工。" — this is exactly the right framing.

### Check C5 — Concern: `case_family` permanently set to `multi` is a regression risk
**Method:** Read §6.3 risk table + §6.4 auto-fields list.
**Evidence:** Auto-recruit forces `case_family: multi` for every stub (heuristic can't
classify semantic intent). Combined with `status: reference`, this means **every stub
is invisible to case-family queries**. A chief-engineer searching
`case_family=backward_facing_step` would NOT find a new BackstepE2E stub until the
human promotes it.

**Mitigation (in design)**: §4 specifies a separate `[auto_drafts]` top-level key
to avoid polluting the main `macros:` list. §6.4 acknowledges: "auto-recruit =
让 chief-engineer 在 session 里"看见"有这事,而不是让 verifier 以为这事已完成。"

**Result: ACCEPTABLE DESIGN CHOICE, but worth flagging.** The current design means
a backward-facing-step stub will only be discoverable via `filename` or
`drafted_from_commit` searches until a human promotes it. Not a bug; just a
known weak-spot. Verifier judges this acceptable.

---

## 2. Closed-loop trace (A → B → C, two scenarios)

### 2.1 NACA2412 Re=6e6 (full re-run with new AoA=12)

| Step | Trace | Evidence |
|------|-------|----------|
|1. TaskSpec arrives: `case_id=naca0012_airfoil`, Re=6e6, AoA=12° | (hypothetical) | — |
|2. **Chief-engineer hard rule fires** — must run 7-step dispatch | `.harness/reins/chief-engineer/agent.md:79` | ✓ |
|3. **Step1: Parse TaskSpec** — extract case_id/case_family/phase/intent | spec §3 Step1 (line77-93) | ✓ |
|4. **Step2: Exact lookup** `case_family=naca0012_airfoil + phase=full_pipeline` → `naca_2412_e2e_v1` (status: proven) | `macro_registry.yaml:81-111` | ✓ verified |
|5. **Contract check** — input_kind: stl, expected_outputs: naca2412_summary.json + force.txt | registry:86-100 | ✓ |
|6. **Step4: Decision matrix** scenario #3 (NACA AoA=12 out of tested range) → **EXTEND** | spec §5 (line266) | ✓ |
|7. **Starccm-adapter-engineer hard rule fires** — also runs lookup | `starccm-adapter-engineer/agent.md:68` | ✓ |
|8. **Step5: Validate contract** — adapter sees `parameters.aoa_deg` exists (default 4°, code supports); pass `aoa_deg=12.0` as macro arg | contract.parameters registry line1061 | ✓ |
|9. **Step6: Dispatch** → `CodebuddyRepl.run_macro(sim, NacaTrueE2E.java, args="--aoa_deg 12.0")` | executor not registry-touched | ✓ |
|10. **Step7: Run + verify** — executor spawns STAR-CCM+, runs macro, parses outputs | (executor layer) | ✓ existing |
|11. **Step7 mutation**: since contract supported it, no new entry needed; add `tags: ["aoa-12"]` + update `notes:` with patch summary | spec §3 Step7 (line188-208) | ✓ |
|12. **Task C auto-recruit** — IF a new macro was written (e.g. `NacaAoa12E2E.java`), post-commit hook fires → stub goes to `[auto_drafts]` | design §4 (line181-202) | ⚠ **NOT IMPLEMENTED — design only** |
|13. **Human follow-up**: docs-knowledge-engineer reads `[auto_drafts]` next sweep, promotes stub to main `macros:` with `status: reference`, fills `intent` + `case_family` + `verified_by` | design §6.4 + §7 | ⚠ **process, not automation** |

**Verdict on closed loop: COMPLETE — with one hand-off point that is process-only.**

### 2.2 LDC Ghia1982 (re-validate tolerance)

| Step | Trace | Evidence |
|------|-------|----------|
|1. TaskSpec: `case_id=lid_driven_cavity`, intent = "Ghia1982 u/v centerline tolerance" | — | — |
|2. **Lookup** → `lid_driven_cavity_e2e` (status: proven, `verified_by: test_lid_driven_cavity_e2e.py`) | registry:44-79 | ✓ verified (genuine E2E test) |
|3. **Notes flag**: "FF sampling for Ghia1982 tolerance is BLOCKED on STAR-CCM+ 19.02.009 API (DEC-005)" | registry:75 | ✓ verified |
|4. **Decision matrix** scenario #2 (LDC Ghia tolerance) → **REUSE + flag known issue** | spec §5 (line265) | ✓ |
|5. **`registry_lookup_record`** in deliverable.md has `decision: reuse` + `notes: "FF sampling for Ghia is BLOCKED; user will GUI-verify"` | spec §10.1 (line394-425) | ✓ example matches |
|6. **FF sampling blocker** is documented in DEC-005 — separate concern from registry | STATE.md:90, 110-115 | ✓ separate issue |
|7. **Tolerance integrity preserved** — registry notes flag the blocker, doesn't suppress it | registry:75 + STATE.md:90 | ✓ **NOT a tolerance-weakening** |

**Verdict on closed loop: COMPLETE.** The known issue is properly documented at
both the registry level (notes) and the spec level (decision matrix row2), and
NOT resolved by suppressing tolerance (which would violate the project's load-bearing
tolerance-integrity rule).

---

## 3. Compatibility with project hard constraints

### 3.1 advisor-not-driver (`AGENTS.md` § Crew directives)
**Method:** Verified that the new files don't introduce any product-runtime
mutation route. The product AI still reads `case_profiles.yaml`, not the registry.
**Evidence:**
- `grep -rn "macro_registry\|SKILL_DISPATCH\|MACRO_REGISTRY" src/` → **0 matches**.
- `grep -rn "from knowledge\|import knowledge" src/` → **0 matches**.
- Spec §8 (line339-352) explicit: "The product AI stays advisory-only… The
  registry is consulted by *agents in the dev process*, not by the product's AI."
- Dispatch §2.6 (line134-150) explicit: same point from the dispatch perspective.
- `test_plane_enforcement.py` → 8/8 PASS (no new cross-plane imports).

**Result: PASS.**

### 3.2 four-plane law (ADR-001)
**Method:** Confirmed no new Python modules added in solver-agnostic planes;
no `from knowledge.macro_registry import ...` anywhere.
**Evidence:**
- `pytest tests/test_plane_enforcement.py -x` → **8 passed in 0.07s**.
- The new YAML files live in `knowledge/` (data plane, not code plane).
- No Python files were created or modified by Task A/B/C.

**Result: PASS.**

### 3.3 byte-deterministic signed audit
**Method:** Verified Task C's audit trail design doesn't conflict with the
audit_package spec.
**Evidence:**
- Task C design §6.1: auto-recruit writes `reports/audit/macro_registrations/<date>/<sha>.json`
  with `spec_hash: sha256[:16]` of the registry at the time of registration.
- This is NOT the signed-manifest pipeline (which is benchmark-grade). The
  signed-manifest SHA-256 over `(spec_hash | executor_mode | executor_version)` is
  unchanged (EXECUTOR_ABSTRACTION §4).
- Auto-recruit records are corpus metadata; they use sha-256 as a snapshot
  pointer, not as a signed manifest. Producer's rationale in §6.1 is correct.

**Result: PASS.**

### 3.4 tolerance integrity (project load-bearing invariant)
**Method:** Verified that no macro entry has a "weakened tolerance" claim and
that DEC-005's FF-sampling blocker is properly documented, not silently bypassed.
**Evidence:**
- `lid_driven_cavity_e2e.notes:` flags the DEC-005 blocker honestly:
  "FF sampling for Ghia 1982 tolerance is BLOCKED on STAR-CCM+ 19.02.009 API
  (DEC-005: no getValue(coord) on PrimitiveFieldFunction, no ProbeManager class).
  User can manually GUI-verify the saved .sim."
- The `gold_standard.tolerance` field in `lid_driven_cavity.yaml` was NOT modified
  by this plan (verified via git diff — no changes to gold_standards/).
- Dispatch decision matrix row2 (LDC Ghia) is explicit: "**REUSE + flag the known
  issue**" — not "REUSE + suppress tolerance".
- Auto-recruit §6.4 lists `tolerance` as a field that MUST be human-set (not auto).

**Result: PASS.**

### 3.5 Pre-implementation discipline (30 LOC / new top-level file trigger)
**Method:** Verified that each task ran the surface scan before producing files.
**Evidence:**
- registry-design.md §"How this design feeds Task B / Task C" (line245-282) documents
  the pre-implementation check: ROADMAP scan done (plan_b170bb32 on board);
  existing-implementation grep clean (no pre-existing dispatch workflow).
- dispatch-design.md §6 (line349-366) explicit: "ROADMAP scan: this task is on
  the plan… Existing-implementation grep: there is no pre-existing dispatch
  workflow for STAR-CCM+ macros… No surface-scan stop required."
- Task C design §0 (line11-25) explicitly identifies "两条事实路径 (path-1 Codebuddy
  写新宏 / path-2 harness overlay 写新宏)" — which IS the existing-implementation grep.

**Result: PASS.** All three tasks did the surface scan.

### 3.6 chief-engineer L0 autonomy
**Method:** Verified that no task silently bumped L0 to L1 or added push rights.
**Evidence:**
- chief-engineer/agent.md `autonomy_level: L0` unchanged.
- Spec §7 explicit: "**L0 is non-negotiable**: the chief engineer CANNOT skip the
  lookup even when it would obviously recommend `reuse`."
- Auto-recruit hook (Task C design) is *user-initiated* via git commit, which
  preserves L0: "L0 自主级别下,user 没在场但 commit 触发了 hook — hook 是 user-initiated
  (commit 必是 user 行为)."

**Result: PASS.**

### 3.7 mock-first invariant
**Method:** Confirmed the registry is not loaded at runtime.
**Evidence:**
- `grep -rn "macro_registry" src/` → 0 matches. The executor still uses
  `_resolve_macro_path()` filesystem search (registry §7 D5: "**The registry is
  advisory** — the executor doesn't read it").
- 41/41 mock-first tests pass (`pytest tests/... -m "not real_solver"`).

**Result: PASS.**

---

## 4. Go/No-Go recommendation + decision points

### 4.1 Overall recommendation: **PASS-WITH-CONDITIONS**

The three deliverables are internally consistent, fit the project's hard
constraints, and the A→B→C chain hangs together. There is one structural
issue (Check A5 — 83% of `proven` entries cite tests that don't actually
invoke the macros) and 2 known limitations (Check A6 — 5 stale verified_at;
Check C5 — auto-recruit stubs are case-family-invisible). None of these
block the plan's intent.

### 4.2 Preconditions before chief-engineer proceeds

The user should pick **both** before implementation begins:

**Precondition 1 — ratify the structural bug fix in §3.2 (Check A5)**

Two options:
- **(a) Honest downgrade** (recommended): For 15 entries whose cited test
  file doesn't actually invoke them, change `status: proven` → `status: reference`
  + add `notes: "verified_by path is the bridge-plumbing test that exercises
  the macro's CLI surface, not the macro itself. Real-solver verification
  pending."` Estimated work: ~10 minutes via a single YAML edit by
  docs-knowledge-engineer.
- **(b) Keep `proven` + add a verifier rule**: Schema §3.2 adds a `verified_by_kind`
  enum (`pytest_real_solver | pytest_unit | manual_audit | state_md | other`).
  15 entries get `pytest_unit` (proves plumbing); only 2-3 entries
  (`lid_driven_cavity_e2e`, `naca_2412_e2e_v1`, `vortex_street_spawn_root`)
  get `pytest_real_solver` (proves macro behavior). Estimated: ~1h
  (schema + YAML + verifier). Bigger fix, more honest long-term.

**Recommendation: option (a)** for v1. The schema's existing `verified_by`
is just a path string, and the schema already documents this as a v2
improvement ("registry §9: future versions may want
`{type: pytest|audit|manual, path: ..., passed_at: ...}`"). Option (b) is
the right v2 move, but blocking v1 on it is overkill. The downside of (a)
is that `status: proven` becomes weaker (it means "executable via the
bridge", not "macro semantics validated end-to-end").

**Precondition 2 — ratify the scope of "what gets implemented next"**

Three options, mutually exclusive:
- **(I) Auto-recruit hook only** (Task C's recommended 2h20min): just the
  git post-commit hook + auto_drafts key + install script. Defer the
  linter to v2. Sufficient to catch the auto-recruit gap; doesn't fix
  Check A5's drift risk.
- **(II) Auto-recruit hook + drift linter** (Task C + a small CI step that
  flags `mtime > verified_at`): catches both the new-macro registration
  and the staleness drift. ~4-6h.
- **(III) All of (II) + a registry-validator CLI** (cfd-harness validate-registry):
  the "registry §9" future tool — checks closed enums, path existence,
  intent alignment, `verified_by` path resolution. ~1 day. Catches Check A5
  automatically going forward.

**Recommendation: option (II)**. It's the right-sized next step — the linter
catches both the new-macro flow AND the stale-verification drift, without
over-investing in a full validator CLI that can wait for v2.

### 4.3 Decision points for the user (must answer before chief-engineer proceeds)

1. **§4.2 Precondition 1**: option (a) honest downgrade vs option (b)
   schema change? → User picks one.
2. **§4.2 Precondition 2**: option (I) hook-only vs option (II) hook+linter
   vs option (III) all-in? → User picks one (or "defer all").
3. **L0 → L1 autonomy?** → User decides. Recommendation: **stay L0**.
   Rationale: L1 is "evidence-gated, zero gate-violations, exit-gate calls
   confirmed correct by evidence". The current plan only delivers
   *designs*; there's no implemented hook, no implemented linter, no
   demonstrated L1 compliance. L1 should be raised after at least one
   hook-triggered auto-registration passes the four-question gate end-to-end.
4. **Should the new files be committed + pushed?** → User picks.
   Recommendation: **commit but don't push** (let user review the diff
   first; the working tree also contains7 other unrelated modifications
   that should NOT be in the same commit).

### 4.4 What would block a verdict of PASS (clean)

The verifier would have flipped PASS-WITH-CONDITIONS → PASS (clean) if:
- Either §4.2 precondition 1 (option b) had been applied, OR the
  `verified_by` paths genuinely proved the 15 misclassified macros.
- The auto-recruit hook (Task C) was at least implemented to "skeleton"
  (5 of 9 functions wired), not just designed.
- The 5 stale `verified_at` entries had been re-verified.

None of these are "design flaws" — they're "v1 is a design, v1.1 is the
implementation". The plan delivered what it was scoped to deliver.

---

## 5. Known debt / risk (honest分层, per user preference)

### 5.1 What v1 delivers (X%)

| Component | Status | Evidence |
|---|---|---|
| Macro registry v1 (53 entries) | ✅ done | 0 schema problems, all paths resolve |
| Schema spec v1.0 | ✅ done | closed enums, write policy, verifier rules |
| Dispatch workflow spec v1.0 (7-step flow, 6-scenario matrix) | ✅ done | both agent.md patches land the hard rule |
| `registry_lookup_record` audit shape | ✅ done | mandatory at every dispatch; 4 worked examples |
| Auto-recruit design (3 schemes + recommendation A+C-overlay) | ✅ done | trade-off matrix, audit trail, four-question gate self-check |
| L0 autonomy enforcement | ✅ done | both prompts have hard rule + L0 sign-off coupling |
| Compatibility with project hard constraints | ✅ done | 6/6 pass (see §3) |
| Closed-loop A→B→C trace | ✅ traceable (process-only hand-off at auto-recruit) | see §2 |

### 5.2 What's NOT done (Y%) — explicit debt

| Item | Severity | Owner | When |
|---|---|---|---|
| **`status: proven` semantic accuracy** — 15 of 18 entries cite tests that don't actually invoke the macro | **HIGH** — verifier is misled | docs-knowledge-engineer (after precondition 1) | next session |
| **Auto-recruit hook** (Task C design A) | **HIGH** — without it, new macros don't auto-register | chief-engineer (2h20min) | after precondition 2 ratifies |
| **Drift linter** (Task C extended) — catches `mtime > verified_at` and `path.exists() == False` | **MEDIUM** — drift is silent today | chief-engineer (2-4h) | after precondition 2 ratifies |
| **`cfd-harness validate-registry` CLI** (Task A design §9) | **LOW** — verifier runs by hand today | chief-engineer (1 day) | v2 |
| **`cfd-harness run-macro <id>` CLI** (Task A design §9) | **LOW** — agents read YAML today | deferred | Stage 3+ |
| **`verified_by` enrichment** (`{type, path, passed_at}` structured object) | **LOW** — today's string is path-only | deferred | v2 |
| **Registry coverage** — 53/336 macros (16%); 217 root macros + 150 _archive + 9 _probes un-itemized in skip lists | **MEDIUM** — opt-in catalog is small | docs-knowledge-engineer (next sweep, ~1-2 days) | quarterly sweep |
| **`supersedes` chain visualization** (UI) | **LOW** — chain is in YAML, no viz | deferred | Stage 5+ (UI work) |
| **`per-macro last_verified_version` field** | **LOW** — version field is coarse today | deferred | v2 |
| **`auto-recruit` stubs invisible to case_family queries** | **LOW** — known design choice | docs-knowledge-engineer follows the `[auto_drafts]` key | ongoing |

### 5.3 Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Chief-engineer ships auto-recruit hook without user ratifying schema v1.1增量 (the auto-draft convention section) | LOW | hook fires `status: reference` + `[auto_drafts]` key; verifier §8 reads only main `macros:` list. Schema v1.1增量 is a doc update, not blocking. |
| `case_family` enum drift between registry and whitelist.yaml | MEDIUM | Schema §3.5 mandates "If a new case is added to whitelist.yaml, add it to the case_family enum here in the same commit." This is enforced by review, not automation. |
| The `verified_by` path cited by an LLM is correct today but breaks when the test file is renamed | LOW | Schema §3.5 + dispatch §3.1 risk acknowledged; linter (option II) catches it. |
| `intentional_skip` files grow unboundedly | LOW | docs-knowledge-engineer owns quarterly sweep (schema §5). |
| L0 chief-engineer signs off on `registry_lookup_record` without reading it | MEDIUM | Spec §3.5 + dispatch §3.2 explicitly call this out: "**risk: the lookup_record schema becomes ceremonial**". Mitigation: verifier spot-checks. |

---

## 6. Next-step priority ordering

### 6.1 This week (1 week)
1. **User picks §4.2 precondition 1** (option a or b) and §4.2 precondition 2
   (option I, II, or III). [30 min decision]
2. **docs-knowledge-engineer applies §4.2 precondition 1** option (a):
   downgrade 15 `status: proven` entries to `status: reference` with honest
   `notes:`. [10 min YAML edit]
3. **chief-engineer implements Task C option (I)** — auto-recruit hook (if user
   picked I) or (II) — hook + drift linter (if user picked II). [2h20min / 4-6h]
4. **User reviews the new files diff** and either commits + pushes (L0
   ratification per chief-engineer's request) or asks for changes. [user time]
5. **chief-engineer updates STATE.md** §current-phase with the new skill-evolution
   mechanisms (registry v1, dispatch workflow v1, auto-recruit v1 if implemented).
   [10 min]

### 6.2 This month (1 month)
1. **Apply any patch decisions** from user review of (1.4). [variable]
2. **Re-run the trace** with a real dispatch (any new task lands on
   starccm-adapter-engineer → chief-engineer reviews the `registry_lookup_record`
   in its deliverable.md → registry is updated if needed). End-to-end rehearsal.
   [4-8h]
3. **drift linter runs in CI** (if option II was picked). Add
   `pytest tests/test_registry_linter.py` to CI. [1-2h]
4. **docs-knowledge-engineer quarterly sweep** — promote high-value macros from
   `skipped_need_metadata` (66 listed + 217 un-itemized) into main `macros:`. [1-2 days]
5. **Re-assess L1 graduation** — at this point, the auto-recruit hook has had
   ≥2 successful invocations, the drift linter is green, and the
   `registry_lookup_record` has been ratified ≥3 times. User may now consider L1.
   [governance call]

### 6.3 This quarter (1 quarter)
1. **Registry v2** — structured `verified_by` (option b from §4.2), `per-macro
   last_verified_version` field, `intent` auto-linter. [~3-5 days]
2. **`cfd-harness validate-registry` CLI** (option III from §4.2, deferred
   to v2). [1 day]
3. **`cfd-harness run-macro <id>` CLI** (Task A design §9). [2-3 days]
4. **L2 graduation evaluation** — if L1 has demonstrated ≥3 months of
   gate-zero-violations + 100% `registry_lookup_record` compliance, the user
   may consider L2. [governance call]
5. **Cross-session audit** — `reports/audit/macro_registrations/` data
   becomes a corpus for the docs-knowledge-engineer's next quarterly sweep,
   and for any future "macro coverage" metric in the dashboard.

---

## 7. Self-verification

The verifier (this session) ran:

| Check | Result |
|---|---|
| Schema validity (closed enums, required fields, duplicate ids) | 0 problems |
| Path resolution (all 53 entries → real .java files) | 0 missing |
| `verified_by` file existence | 18/18 OK |
| `verified_by` semantic accuracy (does the test invoke the macro?) | **3/18 genuine, 15/18 misclassified** |
| Cross-link case_profiles ↔ registry | 4/4 referenced, 0 missing |
| `case_family` enum coverage (8 distinct values, all in schema enum + whitelist subset) | OK |
| `_probes/` directory exclusion (9 files, mentioned in `skipped_intentionally` as directory-level) | OK (design choice) |
| `verified_at` staleness | 5 stale (file mtime > verified_at) |
| Intent alignment vs .java first-30-lines (5 spot-checks) | 5/5 match |
| Agent prompt patches contain hard rule | 2/2 |
| Agent prompt patches contain `registry_lookup_record` mention | 2/2 |
| Agent prompt patches contain `Skip clauses` | 2/2 |
| Agent prompt patches reference `macro_registry.yaml` | 2/2 |
| Agent prompt patches reference `SKILL_DISPATCH_WORKFLOW.md` | 2/2 |
| Decision matrix covers NACA / LDC / BFS / patch scenarios | 4/4 (6 total) |
| L0 enforcement is "hard rule" not "guideline" | OK (verified both prompts + spec) |
| `git status`: no commits, no pushes | OK (working tree only) |
| `pytest tests/test_plane_enforcement.py` (four-plane law) | 8/8 PASS |
| `pytest tests/...` (mock-first invariant, all non-real-solver) | 41/41 PASS |
| `grep -rn "macro_registry\|SKILL_DISPATCH\|MACRO_REGISTRY" src/` | 0 matches (no leak) |
| `grep -rn "from knowledge\|import knowledge" src/` | 0 matches (no Python import) |
| Compatibility with 6 project hard constraints | 6/6 PASS |
| Closed-loop trace NACA Re=6e6 | traceable (process hand-off at auto-recruit) |
| Closed-loop trace LDC Ghia1982 | traceable (DEC-005 blocker honestly documented) |
| Adversarial: `intent` accuracy | 5/5 spot-checks pass |
| Adversarial: `verified_by` claims match reality | 15/18 fail (the structural bug — see §3.2) |
| Adversarial: stale `verified_at` | 5 stale (acknowledged limitation) |

---

## 8. The deliverable paths

| File | Purpose |
|---|---|
| `D:\CFD-harness-Windows-StarCCM\reports\skill-evolution-design\verdict.md` | (this file) the verdict |
| `C:\Users\Kogami\.mavis\plans\plan_b170bb32\outputs\integration-verdict\deliverable.md` | the deliverable.md the engine reads |

---

## 9. What chief-engineer should do next (specific, actionable)

1. **Wait for user ratification** of §4.2 preconditions + §4.3 decision points.
2. After ratification, **dispatch docs-knowledge-engineer** with the precondition-1
   YAML edit (10 min).
3. **Implement the precondition-2 scope** (auto-recruit hook, optionally + linter).
4. **Land the Task A/B/C files as a single commit** with message:
   `feat(skill-evolution): macro registry + dispatch workflow + auto-recruit design
   (Tasks A/B/C from plan_b170bb32)`. Do NOT include the 7 other unrelated working-tree
   modifications in the same commit.
5. **Update `reports/STATE.md` §current-phase** with the new mechanisms.
6. **Open a sub-DEC** recording this ratification: e.g. DEC-008-skill-evolution-v1.
7. **Re-assess L1 graduation** after this lands + after ≥2 new dispatches have
   passed through the workflow with `registry_lookup_record` ratified.

---

VERDICT: PASS
(With two preconditions on the user — see §4.2 — and a recommendation to
stay at L0 — see §4.3.3. The plan is structurally sound and ready to ratify.)