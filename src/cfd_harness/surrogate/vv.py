"""Surrogate accuracy V&V — tolerance-gated verdict + signed audit.

Bridges the surrogate metrics (R²/MAE/RMSE/...) to the project's honest,
signed V&V framework so a surrogate's accuracy claim is as tamper-evident
and citable as a CFD benchmark.

Honesty rule (mirrors the CFD MOCK ceiling, EXECUTOR_ABSTRACTION §6.1):
a surrogate trained on SYNTHETIC / mock data (``data_source != "real"``)
can NEVER be ``validated`` — its verdict ceiling is WARN. This prevents a
surrogate fit on `generate_mock_data` from ever being cited as a validated
result, exactly as a MOCK CFD run is capped at WARN.

This module is purely additive: it imports the surrogate metrics and the
audit package; it does not modify the training pipeline. Sign the audit with
a real key (see DEC-010) and verify it with the SAME tool as a CFD audit:
``python -m cfd_harness.audit_package.verify <audit.json>``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
from cfd_harness.surrogate.metrics import evaluate_all

__all__ = [
    "DATA_SOURCE_REAL",
    "DATA_SOURCE_MOCK",
    "SurrogateAcceptance",
    "SurrogateVerdict",
    "evaluate_surrogate",
    "surrogate_manifest",
    "build_signed_surrogate_audit",
]

DATA_SOURCE_REAL = "real"   # held-out real-solver / experimental targets
DATA_SOURCE_MOCK = "mock"   # synthetic targets (generate_mock_data) — never validated


@dataclass(frozen=True)
class SurrogateAcceptance:
    """Acceptance thresholds for a surrogate's held-out accuracy.

    A surrogate PASSes only if every set threshold is met. Unset thresholds
    (``inf`` / ``-inf``) are not gated. Defaults require a strong fit
    (R² ≥ 0.95) and leave the error magnitudes ungated unless specified.
    """
    min_r2: float = 0.95
    max_mae: float = float("inf")
    max_rmse: float = float("inf")
    max_relative_error: float = float("inf")


@dataclass(frozen=True)
class SurrogateVerdict:
    """The surrogate accuracy verdict (solver-agnostic, audit-ready)."""
    level: str                                   # PASS | WARN | FAIL
    data_source: str                             # "real" | "mock"
    metrics: Dict[str, float] = field(default_factory=dict)
    failing: List[str] = field(default_factory=list)
    mock_ceiling_applied: bool = False

    @property
    def is_mock(self) -> bool:
        return self.data_source != DATA_SOURCE_REAL

    @property
    def is_validated(self) -> bool:
        """A surrogate is `validated` iff PASS AND trained against real
        (not synthetic) targets. Mock-data surrogates never validate."""
        return self.level == "PASS" and not self.is_mock

    def __bool__(self) -> bool:
        return self.is_validated


def evaluate_surrogate(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    acceptance: Optional[SurrogateAcceptance] = None,
    *,
    data_source: str = DATA_SOURCE_MOCK,
    label: str = "test",
) -> SurrogateVerdict:
    """Gate a surrogate's held-out predictions against acceptance thresholds.

    ``y_true`` / ``y_pred`` are ``(N, k)`` arrays (e.g. columns Cl, Cd).
    Returns a verdict whose level is FAIL if any threshold is missed, else
    PASS — then clamped to WARN when ``data_source`` is not "real" (the
    synthetic-data ceiling). Mirrors the CFD verifier's honesty contract.
    """
    acceptance = acceptance or SurrogateAcceptance()
    yt = np.asarray(y_true, dtype=float)
    yp = np.asarray(y_pred, dtype=float)
    if yt.shape != yp.shape:
        raise ValueError(f"shape mismatch: y_true{yt.shape} vs y_pred{yp.shape}")
    if yt.ndim != 2:
        raise ValueError(f"expected (N, k) arrays, got ndim={yt.ndim}")

    m = evaluate_all(yt, yp, label=label)
    r2v = m[f"{label}_r2"]
    mae_v = m[f"{label}_mae"]
    rmse_v = m[f"{label}_rmse"]
    rel_v = m[f"{label}_relative_error"]

    failing: List[str] = []
    if r2v < acceptance.min_r2:
        failing.append(f"r2={r2v:.4f}<min_r2={acceptance.min_r2}")
    if mae_v > acceptance.max_mae:
        failing.append(f"mae={mae_v:.4g}>max_mae={acceptance.max_mae:.4g}")
    if rmse_v > acceptance.max_rmse:
        failing.append(f"rmse={rmse_v:.4g}>max_rmse={acceptance.max_rmse:.4g}")
    if rel_v > acceptance.max_relative_error:
        failing.append(
            f"relative_error={rel_v:.4g}>max_relative_error={acceptance.max_relative_error:.4g}"
        )

    level = "FAIL" if failing else "PASS"
    # Synthetic-data ceiling: a mock-trained surrogate never reaches PASS.
    ceiling = (data_source != DATA_SOURCE_REAL) and level == "PASS"
    if ceiling:
        level = "WARN"

    return SurrogateVerdict(
        level=level,
        data_source=data_source,
        metrics=m,
        failing=failing,
        mock_ceiling_applied=ceiling,
    )


def surrogate_manifest(
    verdict: SurrogateVerdict,
    *,
    model_id: str,
    contract_hash: str = "surrogate",
    spec_version: str = "0.3",
) -> Manifest:
    """Project a SurrogateVerdict onto the (signable) audit Manifest.

    Reuses the CFD audit Manifest so a surrogate accuracy claim is signed,
    byte-deterministic, and verifiable with the same tooling. The accuracy
    gate maps onto comparison_all_pass / comparison_failing; convergence and
    physics are not applicable and reported as trivially passing.
    """
    return Manifest(
        schema_version=SCHEMA_VERSION,
        case_id=model_id,
        executor_mode="surrogate",
        contract_hash=contract_hash,
        spec_version=spec_version,
        verdict_level=verdict.level,
        is_validated=verdict.is_validated,
        is_mock=verdict.is_mock,
        comparison_all_pass=(not verdict.failing),
        comparison_failing=list(verdict.failing),
        convergence_all_pass=True,   # n/a for a surrogate
        physics_all_pass=True,       # n/a for a surrogate
    )


def build_signed_surrogate_audit(
    verdict: SurrogateVerdict,
    key: bytes,
    *,
    model_id: str,
    key_source: str = "provided",
) -> Dict[str, Any]:
    """Produce a signed audit dict (same shape as the CFD CLI's audit.json),
    verifiable via ``cfd_harness.audit_package.verify``.

    ``key`` must be a real >=32-byte secret for a trusted audit; see DEC-010.
    """
    from cfd_harness.audit_package.sign import Signer

    manifest = surrogate_manifest(verdict, model_id=model_id)
    sig = Signer(key).sign(manifest)
    return {
        "manifest": manifest.to_dict(),
        "signature": {
            "digest": sig.digest,
            "hmac": sig.hmac,
            "key_id": sig.key_id,
            "algorithm": sig.algorithm,
            "signed_at": sig.signed_at,
        },
        "signing": {
            "key_source": key_source,
            "trusted": key_source == "provided",
        },
        # Non-signed, human-facing accuracy detail.
        "surrogate_metrics": dict(verdict.metrics),
        "data_source": verdict.data_source,
    }
