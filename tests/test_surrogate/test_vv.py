"""Tests for surrogate accuracy V&V + signed audit (bridges surrogate ↔ DEC-010)."""
from __future__ import annotations

import numpy as np

from cfd_harness.audit_package.sign import DEV_UNSIGNED_KEY
from cfd_harness.audit_package.verify import verify_audit
from cfd_harness.surrogate.vv import (
    DATA_SOURCE_MOCK,
    DATA_SOURCE_REAL,
    SurrogateAcceptance,
    build_signed_surrogate_audit,
    evaluate_surrogate,
    surrogate_manifest,
)

_PROD_KEY = b"surrogate-prod-secret-key-32+bytes!!"


def _perfect():
    y = np.array([[0.20, 0.010], [0.45, 0.012], [0.60, 0.015], [0.30, 0.011]])
    return y, y.copy()  # y_pred == y_true -> R²=1.0


def _poor():
    y_true = np.array([[0.20, 0.010], [0.45, 0.012], [0.60, 0.015], [0.30, 0.011]])
    y_pred = y_true + np.array([[0.5, 0.5]] * 4)  # large bias -> R² << 0.95
    return y_true, y_pred


def test_real_perfect_fit_validates():
    yt, yp = _perfect()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_REAL)
    assert v.level == "PASS"
    assert v.is_validated is True
    assert v.failing == []
    assert v.metrics["test_r2"] == 1.0


def test_mock_perfect_fit_is_clamped_to_warn_never_validated():
    """The honesty ceiling: a synthetic-data surrogate never validates."""
    yt, yp = _perfect()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_MOCK)
    assert v.level == "WARN"               # PASS clamped to WARN
    assert v.mock_ceiling_applied is True
    assert v.is_validated is False
    assert v.is_mock is True


def test_poor_fit_fails_even_on_real_data():
    yt, yp = _poor()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_REAL)
    assert v.level == "FAIL"
    assert v.is_validated is False
    assert any("r2=" in f for f in v.failing)


def test_acceptance_thresholds_are_gated():
    yt, yp = _perfect()  # R²=1, mae=0
    strict = SurrogateAcceptance(min_r2=0.99, max_mae=1e-9)  # mae=0 passes, r2=1 passes
    assert evaluate_surrogate(yt, yp, strict, data_source=DATA_SOURCE_REAL).level == "PASS"
    # Now make mae gate impossible to meet with a tiny bias.
    yp2 = yt + 1e-3
    v = evaluate_surrogate(yt, yp2, SurrogateAcceptance(min_r2=-1e9, max_mae=1e-6),
                           data_source=DATA_SOURCE_REAL)
    assert v.level == "FAIL"
    assert any("mae=" in f for f in v.failing)


def test_manifest_maps_verdict_fields():
    yt, yp = _perfect()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_REAL)
    m = surrogate_manifest(v, model_id="mlp_rotor37_v1")
    assert m.case_id == "mlp_rotor37_v1"
    assert m.executor_mode == "surrogate"
    assert m.verdict_level == "PASS"
    assert m.is_validated is True
    assert m.is_mock is False
    assert m.comparison_all_pass is True


def test_signed_surrogate_audit_verifies_with_dec010_tooling():
    """A surrogate audit is signed + verified by the SAME machinery as CFD."""
    yt, yp = _perfect()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_REAL)
    audit = build_signed_surrogate_audit(v, _PROD_KEY, model_id="mlp_rotor37_v1")

    # Verifies under the signing key (trusted, real key_source).
    res = verify_audit(audit, _PROD_KEY)
    assert res.accepted is True
    assert res.trusted is True
    assert res.manifest.executor_mode == "surrogate"
    assert audit["surrogate_metrics"]["test_r2"] == 1.0

    # Tamper a signed field -> verification fails (the manifest is bound).
    tampered = {**audit, "manifest": {**audit["manifest"], "comparison_all_pass": False}}
    assert verify_audit(tampered, _PROD_KEY).accepted is False


def test_dev_unsigned_surrogate_audit_is_untrusted():
    yt, yp = _perfect()
    v = evaluate_surrogate(yt, yp, data_source=DATA_SOURCE_REAL)
    audit = build_signed_surrogate_audit(
        v, DEV_UNSIGNED_KEY, model_id="m", key_source="dev-unsigned"
    )
    assert verify_audit(audit, DEV_UNSIGNED_KEY).accepted is False          # default rejects
    assert verify_audit(audit, DEV_UNSIGNED_KEY, require_trusted=False).accepted is True
