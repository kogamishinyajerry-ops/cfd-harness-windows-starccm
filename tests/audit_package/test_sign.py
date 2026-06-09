"""Tests for the audit package's manifest + signing."""
from __future__ import annotations

import pytest

from cfd_harness.audit_package import ManifestBuilder, Signer
from cfd_harness.audit_package.manifest import SCHEMA_VERSION
from cfd_harness.audit_package.serialize import serialize_manifest


def test_manifest_schema_version():
    assert SCHEMA_VERSION == 1


def test_sign_then_verify(ldc_task_spec, hmac_key):
    """A signed manifest MUST verify with the same key."""
    from cfd_harness.executor.mock import MockExecutor
    from cfd_harness.auto_verifier import AutoVerifier
    from cfd_harness.auto_verifier.config import VerifierConfig

    mock = MockExecutor()
    run = mock.execute(ldc_task_spec)
    config = VerifierConfig()
    verifier = AutoVerifier(config)
    verdict = verifier.verify(run, ldc_task_spec, gold_anchor=ldc_task_spec.gold_anchor or None)
    manifest = ManifestBuilder().build(ldc_task_spec, run, verdict)
    signer = Signer(hmac_key)
    sig = signer.sign(manifest)
    assert sig.verify(manifest, hmac_key) is True


def test_modified_manifest_fails_verification(ldc_task_spec, hmac_key):
    """Modifying any field after signing MUST break the signature."""
    from dataclasses import replace
    from cfd_harness.executor.mock import MockExecutor
    from cfd_harness.auto_verifier import AutoVerifier
    from cfd_harness.auto_verifier.config import VerifierConfig

    mock = MockExecutor()
    run = mock.execute(ldc_task_spec)
    config = VerifierConfig()
    verifier = AutoVerifier(config)
    verdict = verifier.verify(run, ldc_task_spec, gold_anchor=ldc_task_spec.gold_anchor or None)
    manifest = ManifestBuilder().build(ldc_task_spec, run, verdict)
    signer = Signer(hmac_key)
    sig = signer.sign(manifest)
    # Tamper: change the case_id
    tampered = replace(manifest, case_id="different_case")
    assert sig.verify(tampered, hmac_key) is False


def test_serialize_manifest_is_deterministic(ldc_task_spec, hmac_key):
    """Two serializations of the same manifest MUST produce identical bytes."""
    from cfd_harness.executor.mock import MockExecutor
    from cfd_harness.auto_verifier import AutoVerifier
    from cfd_harness.auto_verifier.config import VerifierConfig

    mock = MockExecutor()
    run = mock.execute(ldc_task_spec)
    config = VerifierConfig()
    verifier = AutoVerifier(config)
    verdict = verifier.verify(run, ldc_task_spec, gold_anchor=ldc_task_spec.gold_anchor or None)
    m1 = ManifestBuilder().build(ldc_task_spec, run, verdict)
    m2 = ManifestBuilder().build(ldc_task_spec, run, verdict)
    assert serialize_manifest(m1) == serialize_manifest(m2)


def test_signer_rejects_empty_key():
    with pytest.raises(ValueError, match="non-empty"):
        Signer(b"")
