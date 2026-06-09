"""VerifierConfig: knobs for the auto-verifier.

Loaded from `knowledge/attestor_thresholds.yaml` (per-case overrides)
or supplied as a constructor argument (for tests).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional

import yaml

_DEFAULT_TOLERANCE_FLOOR = 0.05  # 5% relative tolerance
_DEFAULT_RESIDUAL_FLOOR = 1e-4   # max allowed residual at the end of solve


@dataclass
class VerifierConfig:
    """Auto-verifier configuration.

    `tolerance_floor`: the default tolerance when a gold standard
    does not specify one. Per-case tolerances in the gold standard
    ALWAYS take precedence.
    `residual_floor`: the largest acceptable final residual.
    `case_overrides`: per-case overrides for the floors (eg. some
    cases may tolerate a higher residual due to turbulence).
    """
    tolerance_floor: float = _DEFAULT_TOLERANCE_FLOOR
    residual_floor: float = _DEFAULT_RESIDUAL_FLOOR
    case_overrides: Dict[str, Dict[str, float]] = field(default_factory=dict)
    thresholds_path: Optional[Path] = None

    @classmethod
    def from_thresholds_yaml(cls, path: Path) -> "VerifierConfig":
        """Load a VerifierConfig from `knowledge/attestor_thresholds.yaml`."""
        if not path.exists():
            return cls(thresholds_path=path)
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return cls(
            tolerance_floor=float(data.get("tolerance_floor", _DEFAULT_TOLERANCE_FLOOR)),
            residual_floor=float(data.get("residual_floor", _DEFAULT_RESIDUAL_FLOOR)),
            case_overrides=dict(data.get("case_overrides", {})),
            thresholds_path=path,
        )

    def for_case(self, case_id: str) -> "VerifierConfig":
        """Return a copy with case-specific overrides applied."""
        if case_id not in self.case_overrides:
            return self
        overrides = self.case_overrides[case_id]
        return VerifierConfig(
            tolerance_floor=overrides.get("tolerance_floor", self.tolerance_floor),
            residual_floor=overrides.get("residual_floor", self.residual_floor),
            case_overrides=self.case_overrides,
            thresholds_path=self.thresholds_path,
        )
