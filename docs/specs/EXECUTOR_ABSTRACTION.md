# EXECUTOR_ABSTRACTION · v0.3 (cfd-harness-windows-starccm)

> **Status**: v0.3 (2026-06-09) — adapted from cfd-harness-unified
> `docs/specs/EXECUTOR_ABSTRACTION.md` v0.2.
>
> **Key delta from v0.2**: added `ExecutorMode.WIN_STARCCM` for Windows +
> STAR-CCM+ 2402 + Codebuddy REPL. The other 4 modes
> (`MOCK`, `DOCKER_OPENFOAM`, `HYBRID_INIT`, `FUTURE_REMOTE`) are
> preserved as-is.

---

## 1. Scope

This document defines the contract between the **V&V engine** (solver-agnostic)
and the **executor layer** (solver-specific). Any concrete solver — be it
OpenFOAM in Docker, STAR-CCM+ on Windows, a remote cloud job, or a synthetic
mock — must implement this contract to plug into the harness.

## 2. ExecutorMode

```python
class ExecutorMode(StrEnum):
    MOCK = "mock"
    DOCKER_OPENFOAM = "docker_openfoam"
    WIN_STARCCM = "win_starccm"           # NEW in v0.3
    HYBRID_INIT = "hybrid_init"
    FUTURE_REMOTE = "future_remote"
```

`WIN_STARCCM` semantics:
- **What it runs**: STAR-CCM+ 2402 local install on Windows, driven by
  `starccm.exe` invoked from the Codebuddy REPL
  (`D:\StarCCM Codebuddy\starccm_cli_repl.py`).
- **Bridge**: `packages/starccm-bridge/` wraps the REPL into a
  `cfd_harness.starccm_adapter.StarCCMExecutor` that conforms to
  `ExecutorAbc`.
- **Verdict ceiling**: full triad `PASS / WARN / FAIL`, same as
  `DOCKER_OPENFOAM` (this is a real solver).
- **Mock label**: TrustGate must surface a `win_starccm_local_install`
  note in `RunReport.notes` so the audit trail shows the executor class
  (not just the contract hash).

## 3. ExecutorStatus

```python
class ExecutorStatus(StrEnum):
    OK = "ok"                              # execution_result populated
    MODE_NOT_APPLICABLE = "mode_not_applicable"     # executor refused (e.g. wrong solver)
    MODE_NOT_YET_IMPLEMENTED = "mode_not_yet_implemented"  # skeleton stub
```

`OK` is the only status with a non-`None` `ExecutionResult`. The other
two have `execution_result=None` and TrustGate routing per §6.1 must
handle the refusal explicitly.

## 4. RunReport

```python
@dataclass(frozen=True)
class RunReport:
    mode: ExecutorMode
    status: ExecutorStatus
    contract_hash: str         # SHA-256 over (spec_sha256 | mode | version)
    version: str               # EXECUTOR_ABSTRACTION spec version
    execution_result: Optional[ExecutionResult] = None
    notes: Tuple[str, ...] = ()  # operator-visible routing/audit metadata
```

`frozen=True` — byte-determinism: RunReport cannot be mutated after
construction, so any TrustGate-side logic that hashes or serializes it
sees a stable shape.

## 5. ExecutorAbc

```python
class ExecutorAbc(ABC):
    MODE: ClassVar[ExecutorMode]
    VERSION: ClassVar[str] = "0.3"

    @property
    def contract_hash(self) -> str: ...     # SHA-256(spec_sha256 | MODE | VERSION)

    @abstractmethod
    def execute(self, task_spec: TaskSpec) -> RunReport: ...
```

Subclass contract:
- Set `MODE` ClassVar to one of the 5 `ExecutorMode` values.
- Implement `execute(task_spec) -> RunReport`.

`contract_hash` is **anchored to the FROZEN spec file** —
`docs/specs/EXECUTOR_ABSTRACTION.md` — not to the executor class identity.
Class renames / module moves do NOT churn signed-manifest bytes; only spec
amendments do.

## 6. Verdict ceiling per mode

| Mode | Verdict ceiling | Notes |
|---|---|---|
| `MOCK` | `WARN` (never `PASS`) | `mock_executor_no_truth_source` |
| `DOCKER_OPENFOAM` | `PASS / WARN / FAIL` | full triad |
| `WIN_STARCCM` | `PASS / WARN / FAIL` | full triad; `win_starccm_local_install` |
| `HYBRID_INIT` | `WARN` | `hybrid_init_invariant_unverified` |
| `FUTURE_REMOTE` | not-yet-implemented | `future_remote_stub_only` |

`MOCK` is the only mode that can NEVER return `PASS` — by design, the
TrustGate ceiling keeps a mock from "passing" anything.

## 7. TaskSpec

```python
@dataclass(frozen=True)
class TaskSpec:
    case_id: str                # e.g. "lid_driven_cavity"
    flow_type: FlowType         # INTERNAL | EXTERNAL | NATURAL_CONVECTION | CONJUGATE | COMPRESSIBLE
    geometry_type: GeometryType # SIMPLE_GRID | IMPORTED_GEOMETRY | CAD_GEOMETRY
    parameters: dict            # Re, Ra, Mach, alpha, etc. (solver-agnostic)
    gold_anchor: str            # path to knowledge/gold_standards/<id>.yaml
    solver_profile: str         # path to solver profile yaml (solver-specific)
    mesh_density: str = "default"  # "mesh_20" | "mesh_40" | "mesh_80" | "mesh_160"
    timeout_s: int = 3600
```

## 8. ExecutionResult

```python
@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    is_mock: bool
    residuals: dict             # {"p": 1e-6, "U": 1e-6, "T": 1e-7}
    key_quantities: dict        # observable-specific
    execution_time_s: float
    raw_output_path: Optional[Path] = None
    case_manifest_hash: Optional[str] = None
```

`is_mock=True` is a MANDATORY tag for the `MOCK` executor. Downstream
code (comparator, audit_package) can use this to gate things
(eg. don't trust gold-comparator `PASS` on `is_mock=True`).

## 9. FlowType and GeometryType

```python
class FlowType(StrEnum):
    INTERNAL = "internal"                    # cavity, channel, duct
    EXTERNAL = "external"                    # cylinder wake, airfoil, flat plate
    NATURAL_CONVECTION = "natural_convection"  # DHC, Rayleigh-Bénard
    CONJUGATE = "conjugate"                  # CHT (solid + fluid)
    COMPRESSIBLE = "compressible"            # supersonic, shock

class GeometryType(StrEnum):
    SIMPLE_GRID = "simple_grid"              # built-in parametric geometry
    IMPORTED_GEOMETRY = "imported_geometry"  # user-provided STL/STEP
    CAD_GEOMETRY = "cad_geometry"            # FreeCAD STEP → STL
```

## 10. Plane assignment (per ADR-001)

`solver-agnostic` packages live in their respective planes:
- `cfd_harness.executor` → `Plane.EXECUTION`
- `cfd_harness.auto_verifier` → `Plane.VERIFICATION`
- `cfd_harness.report_engine` → `Plane.REPORTING`
- `cfd_harness.audit_package` → `Plane.AUDIT`
- `cfd_harness.metrics` → `Plane.METRICS`

`solver-specific` packages:
- `cfd_harness.starccm_adapter` → `Plane.ADAPTER_STARCCM`
- `packages/starccm-bridge` → `Plane.ADAPTER_STARCCM`

Cross-plane imports are forbidden by `ADR-001`. The ExecutorAbc
contract is the only bridge.

## 11. Spec versioning

`SPEC_VERSION = "0.3"` in `cfd_harness.executor.base`. Bumping the spec
bumps this constant in lockstep; the `contract_hash` is derived from
the spec file content + mode + version, so a spec amendment
invalidates all previously-signed audit packages (intended — the
contract has moved).

## 12. Reference impl

`cfd_harness.executor.mock.MockExecutor` is the canonical reference for
`MOCK` mode; it stamps the `mock_executor_no_truth_source` note and
returns synthetic `ExecutionResult` per `flow_type`. The
`WIN_STARCCM` reference impl is at
`cfd_harness.starccm_adapter.executor.StarCCMExecutor` (Stage 3+);
its real impl is in `packages/starccm-bridge/` which calls
`D:\StarCCM Codebuddy\starccm_cli_repl.py` over its REPL.
