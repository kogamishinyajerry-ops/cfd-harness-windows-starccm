# MACRO_REGISTRY_SCHEMA · v1.0 (cfd-harness-windows-starccm)

> **Status**: v1.0 (2026-06-11) — first cut, companion to
> `knowledge/macro_registry.yaml`.
>
> **Audience**: any agent (chief-engineer, starccm-adapter-engineer,
> docs-knowledge-engineer, future session) that needs to find, route, or
> extend a STAR-CCM+ Java macro.

---

## 1. Purpose

`D:\StarCCM Codebuddy\macros\` holds **336 STAR-CCM+ Java macros** as of
2026-06-11 (top-level + `_archive/`). They are the authoritative
implementation catalog for what the `D:\StarCCM Codebuddy` REPL can do.
Harness-side macros (currently just `D:\CFD-harness-Windows-StarCCM\macros\LidDrivenCavity.java`)
**overlay** on top of that catalog — they win on same-name conflicts via
`_resolve_macro_path()` in `src/cfd_harness/starccm_adapter/executor.py:204-212`.

`macro_registry.yaml` is the **human + LLM-readable index** of the catalog.
Reading the registry, an agent should be able to answer:

1. "For a LDC case, which macro do I run?" — find `lid_driven_cavity_e2e` + `LidDrivenCavity.java`
2. "What does `CliSolveInitOnly` do, and is it proven?" — find the entry, see `intent`, `status`, `verified_by`
3. "I'm adding a new macro `MyNewMacro.java`. Where do I register it?" — this doc, §4
4. "I have a Re=6e6 NACA run. Does the macro handle AoA=2°?" — read `contract.parameters`, `contract.env`

The registry is the entry point; the actual files live where the file
system says they live (`path` field). We do **not** duplicate macro
content into the registry — we annotate it.

## 2. File location

```
D:\CFD-harness-Windows-StarCCM\knowledge\macro_registry.yaml
```

Path is solver-agnostic (sits next to `whitelist.yaml`, `case_profiles.yaml`,
`skill_index.yaml`). The macros themselves are solver-specific and live
under `D:\StarCCM Codebuddy\macros\` (or `D:\CFD-harness-Windows-StarCCM\macros\`
when overlaying).

## 3. Schema

### 3.1 Top-level

| Field | Type | Required | Description |
|---|---|---|---|
| `version` | int | yes | Schema version. Bumped on breaking field changes. v1. |
| `description` | string | no | One-paragraph what-this-file-is. |
| `source` | string | yes | Origin of the catalog (e.g. `D:\StarCCM Codebuddy\macros\ as of 2026-06-11`) |
| `generated_at` | ISO-8601 | yes | When this snapshot was last manually curated. |
| `curator` | string | yes | Who owns the next refresh (e.g. `docs-knowledge-engineer`). |
| `macros` | list[entry] | yes | The catalog. See §3.2. |

### 3.2 Per-entry fields

A registry entry is one `Java macro` or one wrapper that groups macros.
Fields:

| Field | Type | Required | Nullable | Description |
|---|---|---|---|---|
| `id` | string | yes | no | Human-readable, `lower_snake_case`. Must be unique. Convention: `<case_or_capability>_<phase>_<version_suffix>`. Examples: `lid_driven_cavity_e2e`, `naca_2412_e2e_v34`, `cli_mesh_gen`, `cli_solve`, `vortex_street_v14`. |
| `path` | string | yes | no | Relative path **anchored to `D:\StarCCM Codebuddy\macros\`** (the catalog root). Backslash on Windows. For harness-overlaying macros (currently only `LidDrivenCavity.java`), the path lives in `D:\CFD-harness-Windows-StarCCM\macros\` and the field carries a `harness://` prefix (see §3.3). |
| `filename` | string | yes | no | Just the basename, e.g. `LidDrivenCavity.java`. Useful for human reading + grep without parsing `path`. |
| `case_family` | enum | yes | no | One of: `lid_driven_cavity`, `naca0012_airfoil`, `circular_cylinder_wake`, `backward_facing_step`, `backward_facing_step_steady`, `duct_flow`, `fully_developed_plane_channel_flow`, `plane_channel_flow`, `axisymmetric_impinging_jet`, `cylinder_crossflow`, `impinging_jet`, `turbulent_flat_plate`, `differential_heated_cavity`, `rayleigh_benard_convection`, `cht_pipe_gnielinski`, `cht_straight_fin`, `apu_complete`, `car_aero`, `building_aero`, `pipe_flow`, `probe`, `diagnostic`, `wrapper`, `template`, `multi`. **Why `multi`**: covers utility macros (mesh, solve, postprocess, report) that apply across many cases. Must match the canonical 16-case `whitelist.yaml:all_cases` list, plus the harness's APU/car/building domain macros, plus `multi` for utility. |
| `phase` | enum | yes | no | One of: `mesh`, `solve`, `postprocess`, `probe`, `export`, `import`, `setup`, `full_pipeline`, `checkpoint`, `wrapper`, `diagnostic`, `template`. `full_pipeline` = walks import → mesh → solve → save. |
| `intent` | string | yes | no | One sentence. What does this macro solve? **Must be derivable from the .java file's first comment block / class header.** Verifier reads the .java top and checks alignment. |
| `contract` | object | yes | no | See §3.4. |
| `starccm_version` | enum | yes | no | One of: `19.02.009` (the active install), `17` (legacy), `16` (older), `15`, `13`, `multi`, `unknown`. The harness runs STAR-CCM+ 19.02.009; macros tagged with other versions may fail. |
| `status` | enum | yes | no | One of: `proven` (real STAR-CCM+ spawn ran end-to-end successfully at least once), `reference` (looks correct, hasn't been smoke-tested in batch), `deprecated` (superseded by a newer entry — set `superseded_by`). |
| `supersedes` | string | no | yes | The `id` of the older version this entry replaces. |
| `superseded_by` | string | no | yes | The `id` of the newer version that replaces this entry. |
| `verified_by` | string | no | yes | Path to the audit / test report that proves the macro works, relative to the harness repo. E.g. `tests/test_lid_driven_cavity_e2e.py` or `reports/audit/lid_driven_cavity/2026-06-10T.../audit.json`. Empty if `status != proven`. |
| `verified_at` | ISO-8601 | no | yes | When the verifying test/audit last passed. |
| `tags` | list[string] | no | no | Free-form: `["k-omega-sst", "steady", "ascii-only"]`, `["cjk-ok"]` (some macros can have CJK in comments), `["reflective-fallback"]`, etc. |
| `notes` | string | no | no | Free text. **Required** if there's a known caveat (e.g. "BC setter fails on v17 but works on 19.02.009"). |
| `line_count` | int | no | no | LOC for quick scan. |
| `authored_by` | string | no | no | Original author if known: `kogami`, `workbuddy-ai`, `claude-opus`, `auto-recorded`. |
| `supersedes_status` | bool | no | no | When `true`, this entry is itself superseded — it's kept for archaeology but not the canonical choice. Default `false`. |

### 3.3 The `harness://` prefix (overlay convention)

Harness-overlaying macros (i.e. those that win on same-name conflicts via
`_resolve_macro_path()`) carry a `path` that does **not** point to the
Codebuddy macros root. The convention:

```yaml
path: "harness://LidDrivenCavity.java"
```

means: "this macro lives at `D:\CFD-harness-Windows-StarCCM\macros\LidDrivenCavity.java`
and takes precedence over any same-named macro in Codebuddy's catalog."
The verifier expands `harness://` to the absolute harness `macros/`
directory. The harness path is fixed (per `AGENTS.md` §Imports & package
layout) so we don't need a per-install config.

The Codebuddy catalog is the **fallback**: if no `harness://` entry
exists, the resolver searches `D:\StarCCM Codebuddy\macros\`.

### 3.4 `contract` sub-object

What the macro accepts (input) and produces (output). Optional fields
are nullable; missing means "not relevant for this macro".

| Field | Type | Required | Nullable | Description |
|---|---|---|---|---|
| `input_kind` | enum | yes | no | One of: `none` (macro builds sim from scratch), `existing_sim` (opens a `.sim`), `stl` (imports one or more STLs), `cad_step` (STEP / IGES — STAR-CCM+ Java API can't import these, so always degrades), `csv_coordinates` (point list), `other`. |
| `output_kind` | enum | yes | no | One of: `modified_sim` (saves a new `.sim`), `summary_json` (writes a JSON to `Cases/Results/`), `csv` (data export), `png_scene` (renders a Scene), `log_only` (just runs and prints), `multiple` (combination). |
| `parameters` | object | no | yes | Dict of named args the macro reads from `getArgs()`. Schema: `{arg_name: {type, default, description}}`. Example: `{re: {type: float, default: 6.0e6}, aoa_deg: {type: float, default: 5.0}, iterations: {type: int, default: 200}}`. |
| `env` | list[string] | no | yes | Env vars the macro reads. Example: `["LDC_ITERS"]` (overrides the 5000 default iters for LDC smoke runs). |
| `expected_outputs` | list[string] | no | yes | Files the macro is expected to write. Absolute Windows paths, or relative to `D:\StarCCM Codebuddy\Cases\Results\`. Example: `["Cases/Results/lid_driven_cavity_summary.json"]`. |
| `license_required` | string | no | yes | `STARCCM_POWER` (full solver + mesher), `STARCCM_DESIGN` (mesh + postprocess, no solver), `STARCCM_POST` (postprocess only), `unknown`. Most production macros need `STARCCM_POWER`. |
| `approximate_wall_s` | int | no | yes | Rough end-to-end wall time, from user's prior runs. E.g. `15` (LDC smoke), `109` (NACA 500-iter). Useful for CLI timeout_s hints. |
| `side_effects` | list[string] | no | yes | State the macro mutates beyond what it outputs. E.g. `["saves_sim_to_case_profiles_path"]`, `["creates_report_monitors"]`, `["disables_multiphase_models"]`. |

### 3.5 Closed enums (verifier will reject values outside)

To make the registry programmatically checkable, the following enums are
**closed sets** (verifier will reject unknown values):

- `case_family`: see §3.2.
- `phase`: see §3.2.
- `starccm_version`: see §3.2.
- `status`: see §3.2.
- `contract.input_kind`: see §3.4.
- `contract.output_kind`: see §3.4.

If a new case is added to `whitelist.yaml`, add it to the `case_family`
enum here in the same commit. If a new phase is invented (e.g.
`uncertainty_quant`), add it to both enums and document why.

## 4. Write policy: who may add / change entries

Three classes of write, in increasing authority:

### 4.1 Auto-curation (none today)

No script scans the macros/ directory and auto-fills entries. The
registry is hand-curated for v1 because the macros are heterogeneous
(probes, journals, scratch — only ~20% are production). Future versions
(`v2`) may add a Python linter that diffs the registry against
`macros/*.java` and flags drift, but it would be advisory only.

### 4.2 Single-macro entry on macro creation

When a **new macro is added to the catalog** (Codebuddy side OR harness
side), the following agents may register it:

- **starccm-adapter-engineer** — primary author, always allowed
- **chief-engineer** — may add for an external contribution or a
  hand-off
- **docs-knowledge-engineer** — may add for archaeology / catalog
  completeness, but must mark `status: reference` and `verified_by: null`

Process:

1. Write the `.java` file first.
2. Read the first 30 lines of the .java (the doc comment + class
   header) to fill `intent`, `contract.input_kind`,
   `contract.output_kind`.
3. Add the entry to `knowledge/macro_registry.yaml` (insert in
   alphabetical order by `id`).
4. Set `status: reference` unless you have personally run it via the
   REPL — `proven` requires a passing test/audit.
5. If `status: proven`, link `verified_by` to the test path that
   proved it.

### 4.3 Whole-registry refresh

When the catalog source directory changes (e.g. user added 30 macros
overnight), the **docs-knowledge-engineer** is responsible for a sweep:

- Diff `D:\StarCCM Codebuddy\macros\*.java` against `path` values in
  the registry.
- Add entries for new files (most will be `status: reference`).
- Mark deleted files' entries as `status: deprecated`, set
  `superseded_by: null` (no replacement), and leave a `notes:` trail.
- Bump `generated_at`.

This sweep is **not blocking**; the registry is allowed to lag the file
system by up to ~1 week. The harness itself doesn't read this YAML at
runtime (yet) — the resolver reads the filesystem directly via
`_resolve_macro_path()`. The registry is for **humans + LLMs** to find
entries quickly.

## 5. Maintenance frequency

| Trigger | Action |
|---|---|
| New macro file added to `D:\StarCCM Codebuddy\macros\` (or harness `macros/`) | Add an entry. See §4.2. |
| New macro replaces an old one (e.g. `NacaTrueE2E` supersedes `CliNaca2412E2E`) | Set `supersedes` on new, `superseded_by` on old. **Both entries stay** in the registry (so the chain is visible). |
| Macro proven in a real run (smoke or E2E) | Flip `status: reference → proven`, fill `verified_by` + `verified_at`. |
| Macro fails in a real run after being `proven` | Don't downgrade silently; add a `notes:` line with the failure date and reason. Leave `status` as-is unless the user ratifies a deprecation. |
| New case added to `whitelist.yaml:all_cases` | Add the case to `case_family` enum in **both** this schema doc and the registry. |
| New phase invented (rare) | Add to `phase` enum. Justify in `notes`. |
| Quarterly sweep | docs-knowledge-engineer diffs the registry against the file system, prunes deleted files, marks stale entries. |

## 6. Usage: agent workflow

A new agent (chief-engineer, or any session starting a fresh CFD task)
should read the registry **before writing any code**:

1. **Receive TaskSpec** (case_id, mesh_density, parameters).
2. **Look up `case_family`** in the registry (filter
   `macros[?case_family=='<case_family>']`).
3. **Pick the entry with the right `phase`**:
   - Need geometry + mesh + solve + save → `phase: full_pipeline`
   - Need just force coefficients from an already-solved sim →
     `phase: postprocess`
   - Need to inspect a sim without running → `phase: probe`
4. **Verify `status: proven`** — if `reference`, warn the user / chief
   that the macro hasn't been run; treat its output as unverified.
5. **Check `contract.parameters` / `env`** to know how to call it:
   - `run_macro(sim_path, macro_path, macro_args=' '.join(args), env=...)`
   - Or use one of the Codebuddy CLI subcommands that wraps it
     (e.g. `vortex-street` wraps `VortexStreet.java`).
6. **Cross-check `case_profiles.yaml`** — the profile's `sim_path` +
   `macros` list should align with the registry's `path` values for
   that case. If they diverge, the registry wins (registry is
   authoritative for macro truth; profiles are runtime resolution).
7. **After running**, log the result. If the run proves the macro
   works in a new context, file a quick patch bumping
   `status: reference → proven` and updating `verified_by` +
   `verified_at`.

### 6.1 Worked example

Task: "Run lid_driven_cavity on WIN_STARCCM with mesh_density=mesh_40."

```yaml
# from knowledge/macro_registry.yaml
- id: lid_driven_cavity_e2e
  case_family: lid_driven_cavity
  phase: full_pipeline
  intent: "Build LDC geometry from STL, set lid-velocity BC, run 5000 iters, save solved .sim, extract u_centerline.csv"
  status: proven
  verified_by: "tests/test_lid_driven_cavity_e2e.py"
  contract:
    input_kind: stl
    output_kind: multiple  # .sim + .csv + .json
    env: ["LDC_ITERS"]
    expected_outputs:
      - "Cases/Results/lid_driven_cavity_solved.sim"
      - "Cases/Results/lid_driven_cavity_summary.json"
      - "Cases/Results/lid_driven_cavity_u_centerline.csv"
    approximate_wall_s: 14
```

Action: dispatch via `executor._resolve_macro_path("LidDrivenCavity.java")`
(harness prefix wins), pass `env={"LDC_ITERS": "500"}` for the
mesh_40 quick run (per executor:204 mapping).

## 7. Relationship to existing files

| File | Relation to `macro_registry.yaml` |
|---|---|
| `knowledge/skill_index.yaml` | **Coexists**. skill_index is about LLM/agent skills (prompts, harness modules) — solver-agnostic. macro_registry is about STAR-CCM+ Java macros — solver-specific. A future task may add a "phase: postprocess → macro_id: cli_post_process" cross-link, but for v1 they're independent indexes. |
| `knowledge/whitelist.yaml` | **Authoritative for `case_family` enum.** Any case in `whitelist.yaml:all_cases` is a valid `case_family` value here (plus `multi` for utility). If you add a case to whitelist, add the same name to the enum here. |
| `knowledge/case_profiles.yaml` | **Runtime resolution layer.** case_profiles is per-case: which `.sim` to open, which macros to run, where to write outputs. The registry is per-macro: what each macro does in isolation. They overlap on `macros` lists — the chief engineer should keep them in sync, with the registry as the source of truth for the macro's *capability* and case_profiles as the source of truth for *which macros a given case uses*. |
| `D:\StarCCM Codebuddy\macros\` (filesystem) | **Catalog source.** The registry mirrors a curated subset; the file system is the runtime source via `_resolve_macro_path()`. The registry is allowed to lag (about 1 week, see §5). |
| `D:\CFD-harness-Windows-StarCCM\macros\` | **Overlay (harness://).** Currently 1 macro (`LidDrivenCavity.java`) + `_probes/` scratch. The overlay wins on same-name conflicts; the registry marks these with `path: "harness://..."`. |
| `docs/specs/EXECUTOR_ABSTRACTION.md` | **Out of scope.** The executor spec defines how the V&V engine talks to executors; it does not enumerate macros. The registry is a layer *below* the executor — it tells the executor which macro to call. |
| `packages/starccm-bridge/src/starccm_bridge/repl.py` | **Runtime consumer.** The bridge's `run_macro(sim_path, macro_path, ...)` is the canonical Stage 3+ spawn. The registry's `path` field is what you pass in. The bridge does not read the registry; it just receives paths. |

## 8. Verification

When the verifier (chief-engineer or test-red-team) audits this file,
it checks:

1. **Schema validity** — every entry has all required fields (§3.2,
   §3.4). Enums are closed (§3.5).
2. **Path existence** — every `path` (after `harness://` expansion for
   overlays) points to a real `.java` file on disk.
3. **`intent` accuracy** — random-spot-check 3 entries; read the .java
   first comment block; the `intent` must match.
4. **Status consistency** — `status: proven` requires a non-empty
   `verified_by`. `status: deprecated` requires a non-empty
   `superseded_by` (unless there's no replacement, in which case set
   `notes:` with the explanation).
5. **`case_family` alignment** — every value is in the closed enum,
   which itself is a strict subset of `whitelist.yaml:all_cases`
   ∪ {`multi`}.
6. **`phase` alignment** — closed enum; the assignment makes sense for
   the `intent` (e.g. a macro that says "generate volume mesh" must
   have `phase: mesh`).
7. **No contradictions with `case_profiles.yaml`** — if a profile
   references macro `Foo.java` in its `macros:` list, there must be
   exactly one registry entry whose `filename: "Foo.java"`.

## 9. Known limitations (v1)

- **No auto-generation** — the registry is hand-curated. A new macro
  added to Codebuddy/macros/ won't appear in the registry until a
  human edits the YAML.
- **No version pinning of macros** — when Codebuddy user updates a
  macro (e.g. `VortexStreet.java` → v15), the `path` doesn't change
  but the code does. The registry trusts that `status: proven` is
  sticky until a re-test fails.
- **`verified_by` is a string, not a structured object** — future
  versions may want `{type: pytest|audit|manual, path: ..., passed_at: ...}`.
  v1 keeps it simple: a relative path that the user can click.
- **`starccm_version` is coarse** — the harness only runs 19.02.009,
  so the version field is mostly historical (which other STAR-CCM+
  builds the macro *might* work on). Future: add
  `last_verified_version` to be precise.
- **No semantic diff between similar macros** — `CliMesh.java` and
  `GenMesh.java` and `CliMeshGen.java` all generate meshes but with
  different scope. A future v2 may add a `supersedes` chain to
  disambiguate.
- **The `multi` case_family bucket is large** — ~30 of the
  highest-value entries are `case_family: multi` (probe + diagnostic
  + utility). If the registry becomes a UI, a tabbed view per
  case_family would be more useful than one giant list.

## 10. Change log

- v1.0 (2026-06-11) — first cut, companion to
  `knowledge/macro_registry.yaml`. 30+ entries with full metadata,
  remainder (probe / diagnostic / archive) marked
  `[skipped-need-metadata]`. Schema fields frozen at §3.
