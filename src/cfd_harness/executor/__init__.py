"""Executor implementations per ExecutorMode.

Plane: EXECUTION. Subpackage-level __init__ re-exports the 5
ExecutorMode implementations:

  - MockExecutor: always works; is_mock=True; verdict ceiling = WARN.
  - DockerOpenFOAMExecutor: real OpenFOAM via Docker (Stage 3+ in
    this repo; ported from cfd-harness-unified for future use).
  - WinStarCCMExecutor: real STAR-CCM+ on Windows via Codebuddy REPL
    (Stage 3+; stub in Stage 1+2).
  - HybridInitExecutor: skeleton (returns MODE_NOT_APPLICABLE until
    reference Docker run anchors the case).
  - FutureRemoteExecutor: skeleton (returns MODE_NOT_YET_IMPLEMENTED).
"""
from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
    SPEC_VERSION,
)
from cfd_harness.executor.mock import MockExecutor

# Skeleton imports — these return MODE_NOT_APPLICABLE /
# MODE_NOT_YET_IMPLEMENTED until Stage 3+ lands the real impls.
from cfd_harness.executor.docker_openfoam import DockerOpenFOAMExecutor
from cfd_harness.executor.win_starccm import WinStarCCMExecutor
from cfd_harness.executor.future_remote import FutureRemoteExecutor
from cfd_harness.executor.hybrid_init import HybridInitExecutor

__all__ = [
    "ExecutorAbc",
    "ExecutorMode",
    "ExecutorStatus",
    "RunReport",
    "SPEC_VERSION",
    "MockExecutor",
    "DockerOpenFOAMExecutor",
    "WinStarCCMExecutor",
    "HybridInitExecutor",
    "FutureRemoteExecutor",
]
