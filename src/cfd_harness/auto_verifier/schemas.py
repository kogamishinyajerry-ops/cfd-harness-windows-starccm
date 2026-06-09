"""Schemas: TypedDict / dataclass shapes used by the auto-verifier.

Solver-agnostic. Defines the JSON-serializable shape of:
  - ComparisonResult (for the report engine)
  - Verdict (the top-level outcome)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

__all__ = ["VerifierReport"]


@dataclass
class VerifierReport:
    """The serialized form of a `Verdict`, ready for the report engine."""
    case_id: str
    executor_mode: str
    is_mock: bool
    level: str                       # PASS | WARN | FAIL
    is_validated: bool
    comparison_all_pass: bool
    comparison_failing: List[str] = field(default_factory=list)
    convergence_all_pass: bool = False
    convergence_failing: List[str] = field(default_factory=list)
    physics_all_pass: bool = False
    physics_failures: List[str] = field(default_factory=list)
    physics_warnings: List[str] = field(default_factory=list)
    suggestions: List[Dict[str, str]] = field(default_factory=list)
    contract_hash: str = ""
    spec_version: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
