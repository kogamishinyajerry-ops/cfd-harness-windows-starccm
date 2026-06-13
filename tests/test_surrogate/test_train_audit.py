"""Tests for the optional signed-accuracy-audit hook in the training pipeline.

The hook is off by default (no behaviour change) and, when on, emits a signed
audit verifiable with the same DEC-010 tooling as a CFD audit. A
mock/synthetic-trained surrogate can never be `validated`.
"""
from __future__ import annotations

import json

from cfd_harness.audit_package.sign import DEV_UNSIGNED_KEY
from cfd_harness.audit_package.verify import verify_audit_file
from cfd_harness.surrogate.train import TrainingConfig, train


def _fast_cfg(tmp_path, **kw) -> TrainingConfig:
    # Tiny, fast MLP — we exercise the audit hook, not model accuracy.
    return TrainingConfig(
        model_type="mlp",
        model_kwargs={"hidden_layer_sizes": (8,), "max_iter": 50},
        n_mock_samples=40,
        seed=1,
        output_dir=str(tmp_path),
        **kw,
    )


def test_no_audit_emitted_by_default(tmp_path):
    res = train(_fast_cfg(tmp_path))
    assert res.audit_path is None


def test_emit_audit_mock_never_validated(tmp_path, monkeypatch):
    monkeypatch.delenv("CFD_HARNESS_SIGN_KEY", raising=False)  # force dev-unsigned
    res = train(_fast_cfg(tmp_path, emit_audit=True))

    assert res.audit_path is not None
    audit = json.loads(open(res.audit_path, encoding="utf-8").read())
    # Inferred mock data source -> ceiling -> never validated.
    assert audit["data_source"] == "mock"
    assert audit["manifest"]["executor_mode"] == "surrogate"
    assert audit["manifest"]["is_validated"] is False
    assert audit["signing"]["key_source"] == "dev-unsigned"
    # Default trust policy rejects dev-unsigned; integrity-only accepts.
    assert verify_audit_file(res.audit_path, DEV_UNSIGNED_KEY).accepted is False
    assert verify_audit_file(
        res.audit_path, DEV_UNSIGNED_KEY, require_trusted=False
    ).accepted is True


def test_emit_audit_trusted_with_real_key(tmp_path, monkeypatch):
    key = "x" * 40
    monkeypatch.setenv("CFD_HARNESS_SIGN_KEY", key)
    res = train(_fast_cfg(tmp_path, emit_audit=True, audit_data_source="real"))

    audit = json.loads(open(res.audit_path, encoding="utf-8").read())
    assert audit["signing"]["key_source"] == "provided"
    assert audit["data_source"] == "real"
    # The signature verifies under the real key (independent of the accuracy verdict).
    assert verify_audit_file(res.audit_path, key.encode("utf-8")).accepted is True
