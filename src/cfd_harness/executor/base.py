"""Executor abstraction per docs/specs/EXECUTOR_ABSTRACTION.md v0.3.

Plane: EXECUTION. Has no cross-plane imports (per ADR-001).

This is the canonical implementation of:
  - §2 ExecutorMode (5 modes: MOCK · DOCKER_OPENFOAM · WIN_STARCCM · HYBRID_INIT · FUTURE_REMOTE)
  - §X.Y / §6.1 routing inputs: RunReport.mode + RunReport.contract_hash
  - §X.Z hybrid-init invariant escape: ExecutorStatus.MODE_NOT_APPLICABLE
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import ClassVar, Optional, Tuple

from cfd_harness.models import ExecutionResult, TaskSpec

__all__ = [
    "ExecutorMode",
    "ExecutorStatus",
    "RunReport",
    "ExecutorAbc",
    "SPEC_VERSION",
    "SPEC_FILE_UNAVAILABLE_SENTINEL",
]

# Canonical version string pinned in the spec frontmatter at
# docs/specs/EXECUTOR_ABSTRACTION.md `version: 0.3`. Bumping the spec
# version requires bumping this constant in lockstep.
SPEC_VERSION = "0.3"

# Per the spec: contract_hash is derived from the FROZEN contract spec
# file. Class renames / module moves do NOT churn signed-manifest bytes;
# only spec changes do. The hash is `lru_cache`d so two `contract_hash`
# calls within the same process read the spec file once.
_SPEC_FILE: Path = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "docs"
    / "specs"
    / "EXECUTOR_ABSTRACTION.md"
)

# Sentinel used when the spec file cannot be read (e.g., installed wheel
# sans docs/). Stable across processes so audit pipelines can detect the
# absence rather than seeing a moving target.
SPEC_FILE_UNAVAILABLE_SENTINEL = "spec_file_unavailable"


@lru_cache(maxsize=1)
def _executor_spec_sha256() -> str:
    """SHA-256 hex of the canonical EXECUTOR_ABSTRACTION.md content bytes.

    Process-cached. Returns ``SPEC_FILE_UNAVAILABLE_SENTINEL`` when the
    file cannot be read.
    """
    try:
        return hashlib.sha256(_SPEC_FILE.read_bytes()).hexdigest()
    except OSError:
        return SPEC_FILE_UNAVAILABLE_SENTINEL


class ExecutorMode(StrEnum):
    """The 5 ExecutorModes per EXECUTOR_ABSTRACTION.md v0.3 §2.

    `StrEnum` (Python 3.11+) — `str(ExecutorMode.MOCK)` yields `'mock'`
    rather than `'ExecutorMode.MOCK'`. This matches the spec's
    representation: the manifest's `executor.mode` field stores the
    string value verbatim.
    """
    MOCK = "mock"
    DOCKER_OPENFOAM = "docker_openfoam"
    WIN_STARCCM = "win_starccm"               # NEW in v0.3
    HYBRID_INIT = "hybrid_init"
    FUTURE_REMOTE = "future_remote"


class ExecutorStatus(StrEnum):
    """Outcome of an `ExecutorAbc.execute(...)` call.

    `OK` is the only status that produces a populated `execution_result`.
    `MODE_NOT_APPLICABLE` and `MODE_NOT_YET_IMPLEMENTED` indicate the
    executor refused to run; `RunReport.execution_result` is None and
    downstream TrustGate routing per §6.1 must handle the refusal
    explicitly.
    """
    OK = "ok"
    MODE_NOT_APPLICABLE = "mode_not_applicable"
    MODE_NOT_YET_IMPLEMENTED = "mode_not_yet_implemented"


@dataclass(frozen=True)
class RunReport:
    """The canonical return type of `ExecutorAbc.execute(...)`.

    Wraps an optional `ExecutionResult` (solver-output dataclass from
    `cfd_harness.models`) with the mode-routing metadata that the
    AuditPackage manifest's additive `executor` field needs.

    `frozen=True` ensures byte-determinism: a `RunReport` cannot be
    mutated post-construction, so any TrustGate-side logic that hashes
    or serializes it sees a stable shape.
    """
    mode: ExecutorMode
    status: ExecutorStatus
    contract_hash: str
    version: str
    execution_result: Optional[ExecutionResult] = None
    notes: Tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.mode, ExecutorMode):
            raise TypeError(
                f"RunReport.mode must be an ExecutorMode value, "
                f"got {type(self.mode).__name__}={self.mode!r}"
            )
        if not isinstance(self.status, ExecutorStatus):
            raise TypeError(
                f"RunReport.status must be an ExecutorStatus value, "
                f"got {type(self.status).__name__}={self.status!r}"
            )
        # Reject a bare string explicitly *before* iterating: tuple("hi")
        # silently char-explodes to ('h', 'i'), which would corrupt note
        # metadata. Callers passing a single note must wrap it themselves.
        if isinstance(self.notes, str):
            raise TypeError(
                f"RunReport.notes must be a tuple of str entries, not a bare "
                f"str. Wrap a single note with a trailing comma: "
                f"got notes={self.notes!r}, expected notes=({self.notes!r},)"
            )
        if not isinstance(self.notes, tuple):
            object.__setattr__(self, "notes", tuple(self.notes))
        for note in self.notes:
            if not isinstance(note, str):
                raise TypeError(
                    f"RunReport.notes entries must be str, "
                    f"got {type(note).__name__}={note!r}"
                )
        if self.status == ExecutorStatus.OK and self.execution_result is None:
            raise ValueError(
                f"RunReport(mode={self.mode!r}, status=OK) requires a populated "
                "execution_result; got None"
            )
        if self.status != ExecutorStatus.OK and self.execution_result is not None:
            raise ValueError(
                f"RunReport(mode={self.mode!r}, status={self.status!r}) must have "
                "execution_result=None; got a populated ExecutionResult"
            )


class ExecutorAbc(ABC):
    """Abstract base for the 5 ExecutorMode implementations.

    Subclass contract:
      - Set `MODE` ClassVar to one of `ExecutorMode` values.
      - Implement `execute(task_spec) -> RunReport`.

    `contract_hash` is computed from a stable identity tuple
    (mode value + spec version + spec-file SHA-256). Per the spec, the
    hash is anchored to the FROZEN contract spec source
    (`docs/specs/EXECUTOR_ABSTRACTION.md`), not to the executor class
    identity — class renames / module moves do NOT churn
    signed-manifest bytes; only spec changes do.

    Different `ExecutorMode` values still produce different hashes
    (mode is part of the identity tuple) so §6.3 reference-run identity
    remains falsifiable per-mode.
    """
    MODE: ClassVar[ExecutorMode]
    VERSION: ClassVar[str] = SPEC_VERSION

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if getattr(cls, "MODE", None) is None:
            raise TypeError(
                f"{cls.__qualname__} must declare a `MODE: ClassVar[ExecutorMode]`"
            )
        if not isinstance(cls.MODE, ExecutorMode):
            raise TypeError(
                f"{cls.__qualname__}.MODE must be an ExecutorMode value, "
                f"got {type(cls.MODE).__name__}"
            )

    @property
    def contract_hash(self) -> str:
        """SHA-256 hex digest of ``(spec_file_sha256 | MODE | VERSION)``.

        Implications:
        - Class rename / module move: hash UNCHANGED.
        - Spec amendment (any byte-level change to the spec file): hash
          CHANGES for ALL modes simultaneously.
        - Different MODE values: hash DIFFERS.
        """
        identity = f"{_executor_spec_sha256()}|{self.MODE.value}|{self.VERSION}"
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()

    @abstractmethod
    def execute(self, task_spec: TaskSpec) -> RunReport:
        """Run the executor against `task_spec` and return a `RunReport`.

        Skeleton subclasses (HybridInit, FutureRemote, WinStarCCM stub)
        return `MODE_NOT_APPLICABLE` / `MODE_NOT_YET_IMPLEMENTED` reports
        without performing real work. P2-T2..T5 fill in real behavior
        in the original; in this repo, Stage 3+ fills in real behavior
        for `StarCCMExecutor`.
        """
        raise NotImplementedError
