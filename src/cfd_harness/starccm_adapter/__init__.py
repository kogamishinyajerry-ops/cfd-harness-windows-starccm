"""STAR-CCM+ adapter: the ADAPTER_STARCCM plane.

Plane: ADAPTER_STARCCM. MAY import EXECUTION, VERIFICATION,
REPORTING, AUDIT, METRICS. MUST NOT be imported by any of those
planes (per ADR-001).

Stage 1+2: this package is a **stub**. The real adapter lands in
Stage 3+ — at that point, `executor.StarCCMExecutor` wraps
`packages.starccm_bridge.CodebuddyRepl` which subprocesses the
user's existing `D:\\StarCCM Codebuddy\\starccm_cli_repl.py`.

This stub exists so the four-plane import law can be enforced
immediately and so `import cfd_harness.starccm_adapter` does not
fail on a fresh venv.
"""
from cfd_harness.starccm_adapter.executor import StarCCMExecutor

__all__ = ["StarCCMExecutor"]
