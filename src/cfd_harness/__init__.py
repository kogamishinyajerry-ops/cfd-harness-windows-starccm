"""cfd-harness-windows-starccm · solver-agnostic V&V engine.

Public surface (re-exported here for `from cfd_harness import ...`):
  - models: TaskSpec, ExecutionResult, FlowType, GeometryType, CFDExecutor
  - executor: ExecutorMode, ExecutorStatus, RunReport, ExecutorAbc,
              MockExecutor, WinStarCCMExecutor (stub), DockerOpenFOAMExecutor (stub)
  - auto_verifier: AutoVerifier, GoldStandardComparator, ConvergenceChecker,
                   PhysicsChecker, CorrectionSuggester
  - report_engine: ReportGenerator, DataCollector, ContractDashboard
  - audit_package: AuditPackage, ManifestBuilder, Signer
  - orchestrator: skill_loader (load_skills_by_type, get_skill, get_categories)

Adapter plane (Stage 3+):
  - starccm_adapter: StarCCMExecutor (real), macro_runner, log_parser, gold_sampler
  - packages.starccm_bridge: subprocess wrapper for the Codebuddy REPL

Four-plane import law (ADR-001):
  - EXECUTION (executor) has no cross-plane imports
  - VERIFICATION (auto_verifier) MAY import EXECUTION only
  - REPORTING (report_engine) MAY import EXECUTION + VERIFICATION
  - AUDIT (audit_package) MAY import EXECUTION + VERIFICATION + REPORTING + METRICS
  - ADAPTER_STARCCM (starccm_adapter, starccm_bridge) MAY import all
"""

from cfd_harness.models import (
    CFDExecutor,
    ExecutionResult,
    FlowType,
    GeometryType,
    TaskSpec,
)

__version__ = "0.1.0"
__all__ = [
    "TaskSpec",
    "ExecutionResult",
    "FlowType",
    "GeometryType",
    "CFDExecutor",
]
