"""Tests for the audit package's manifest + signing."""
from __future__ import annotations

import pytest

from cfd_harness.audit_package import ManifestBuilder, Signer
from cfd_harness.audit_package.manifest import SCHEMA_VERSION
from cfd_harness.audit_package.serialize import serialize_manifest


def test_manifest_schema_version():
    assert SCHEMA_VERSION == 2  # v2: signing hardened (DEC-010)


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
    with pytest.raises(ValueError, match="at least 32 bytes"):
        Signer(b"")


def test_signer_rejects_short_key():
    """Keys below 256 bits are rejected (DEC-010 H-1)."""
    with pytest.raises(ValueError, match="at least 32 bytes"):
        Signer(b"too-short-key-under-32-bytes")  # 28 bytes


def _validated_manifest(case_id="naca0012_airfoil"):
    """A manifest claiming a validated, real-solver run (the thing an
    attacker would forge)."""
    from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
    return Manifest(
        schema_version=SCHEMA_VERSION,
        case_id=case_id,
        executor_mode="win_starccm",
        contract_hash="deadbeef" * 8,
        spec_version="0.3",
        verdict_level="PASS",
        is_validated=True,
        is_mock=False,
        comparison_all_pass=True,
        convergence_all_pass=True,
        physics_all_pass=True,
    )


def test_signature_carries_key_id(hmac_key):
    """The signature records a non-secret fingerprint of the signing key,
    so a verifier can tell WHICH key signed it (DEC-010 C-2)."""
    from cfd_harness.audit_package.sign import key_fingerprint
    sig = Signer(hmac_key).sign(_validated_manifest())
    assert sig.key_id == key_fingerprint(hmac_key)
    assert sig.key_id != ""


def test_verify_fails_against_a_different_key(hmac_key):
    """A signature made with key A must NOT verify against key B."""
    other_key = b"a-totally-different-but-valid-32B-key!"
    m = _validated_manifest()
    sig = Signer(hmac_key).sign(m)
    assert sig.verify(m, hmac_key) is True
    assert sig.verify(m, other_key) is False  # key_id + HMAC both differ


def test_dev_unsigned_forgery_is_attributable_and_untrusted():
    """The hardened scheme can't stop someone signing with a *known* key,
    but the audit's key_id reveals it was the dev-unsigned key, and it never
    verifies under a real production key (DEC-010 C-1/C-2)."""
    from cfd_harness.audit_package.sign import DEV_UNSIGNED_KEY, DEV_UNSIGNED_KEY_ID

    forged = _validated_manifest()
    sig = Signer(DEV_UNSIGNED_KEY).sign(forged)
    # 1) The signature self-identifies the dev key -> a verifier blocklists it.
    assert sig.key_id == DEV_UNSIGNED_KEY_ID
    # 2) It does NOT verify under a real production secret.
    prod_key = b"a-real-production-secret-key-of-32+bytes"
    assert sig.verify(forged, prod_key) is False


def test_backdating_signed_at_breaks_verification(hmac_key):
    """signed_at is bound into the signed payload, so altering it (e.g.
    backdating) breaks the signature (DEC-010 C-3)."""
    from dataclasses import replace
    m = _validated_manifest()
    sig = Signer(hmac_key).sign(m)
    assert sig.verify(m, hmac_key) is True
    backdated = replace(sig, signed_at="2000-01-01T00:00:00+00:00")
    assert backdated.verify(m, hmac_key) is False


def test_serialize_rejects_nan():
    """A nan/inf in any field raises instead of emitting non-RFC JSON
    tokens that verifiers parse inconsistently (DEC-010 H-3)."""
    from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
    m = Manifest(
        schema_version=SCHEMA_VERSION, case_id="x", executor_mode="mock",
        contract_hash="h", spec_version="0.3", verdict_level="WARN",
        is_validated=False, is_mock=True, comparison_all_pass=False,
        suggestions=[{"category": "a", "severity": "b", "message": float("nan")}],
    )
    with pytest.raises(ValueError):
        serialize_manifest(m)


def test_serialize_nfc_normalizes_unicode():
    """NFC and NFD forms of the same text serialize to identical bytes, so an
    untampered manifest does not raise a false tamper alarm across platforms
    (DEC-010 M-1)."""
    import unicodedata
    from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
    nfc = unicodedata.normalize("NFC", "café")
    nfd = unicodedata.normalize("NFD", "café")
    assert nfc != nfd  # different code-point sequences
    common = dict(
        schema_version=SCHEMA_VERSION, executor_mode="mock", contract_hash="h",
        spec_version="0.3", verdict_level="WARN", is_validated=False,
        is_mock=True, comparison_all_pass=False,
    )
    assert serialize_manifest(Manifest(case_id=nfc, **common)) == \
        serialize_manifest(Manifest(case_id=nfd, **common))
