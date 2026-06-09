"""V&V metrics: simple metrics accumulator (placeholder for Stage 2).

Plane: METRICS.

Stage 1+2 stub: a simple counter of V&V runs and a tally of
verdicts. Stage 3+ may add per-case error distributions, GCI
(Grid Convergence Index) computation, etc.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List

__all__ = ["VAndVMetrics", "MetricsAccumulator"]


@dataclass
class VAndVMetrics:
    """A snapshot of the V&V metrics."""
    total_runs: int = 0
    verdict_counts: Dict[str, int] = field(default_factory=dict)
    pass_rate: float = 0.0
    is_mock_runs: int = 0
    real_solver_runs: int = 0

    def to_dict(self) -> dict:
        return {
            "total_runs": self.total_runs,
            "verdict_counts": dict(self.verdict_counts),
            "pass_rate": self.pass_rate,
            "is_mock_runs": self.is_mock_runs,
            "real_solver_runs": self.real_solver_runs,
        }


class MetricsAccumulator:
    """Accumulates V&V run verdicts and exposes a MetricsAccumulator.snapshot()."""
    def __init__(self) -> None:
        self._levels: List[str] = []
        self._is_mock: List[bool] = []

    def record(self, level: str, is_mock: bool) -> None:
        if level not in {"PASS", "WARN", "FAIL"}:
            raise ValueError(f"verdict level must be PASS/WARN/FAIL, got {level!r}")
        self._levels.append(level)
        self._is_mock.append(is_mock)

    def snapshot(self) -> VAndVMetrics:
        if not self._levels:
            return VAndVMetrics()
        counts = Counter(self._levels)
        # PASS rate is computed on real-solver runs only (MOCK can
        # never reach PASS per the §6.1 ceiling; counting them would
        # understate the real pass rate).
        real_levels = [
            l for l, m in zip(self._levels, self._is_mock) if not m
        ]
        real_pass = sum(1 for l in real_levels if l == "PASS")
        rate = (real_pass / len(real_levels)) if real_levels else 0.0
        return VAndVMetrics(
            total_runs=len(self._levels),
            verdict_counts=dict(counts),
            pass_rate=rate,
            is_mock_runs=sum(1 for m in self._is_mock if m),
            real_solver_runs=sum(1 for m in self._is_mock if not m),
        )
