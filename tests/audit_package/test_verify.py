"""Tests for the executable audit verifier (DEC-010 trust policy)."""
from __future__ import annotations

import json

from cfd_harness.audit_package.manifest import Manifest, SCHEMA_VERSION
from cfd_harness.audit_package.sign import (
    DEV_UNSIGNED_KEY,
    MIN_KEY_BYTES,
    Signer,
)
from cfd_harness.audit_package.verify import (
    verify_audit,
    verify_audit_file,
)
from cfd_harness.audit_package.verify import _main as verify_main

_PROD_KEY = b"prod-secret-key-padded-past-32-bytes!!"


def _validated_manifest(case_id="naca0012_airfoil"):
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


def _audit_payload(manifest, key, key_source="provided"):
    """Mirror the cli/run.py audit.json structure."""
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
            "min_key_bytes": MIN_KEY_BYTES,
        },
    }


def test_verify_accepts_trusted_audit():
    m = _validated_manifest()
    audit = _audit_payload(m, _PROD_KEY, key_source="provided")
    res = verify_audit(audit, _PROD_KEY, expected_key_id=audit["signature"]["key_id"])
    assert res.accepted is True
    assert res.hmac_ok is True
    assert res.trusted is True
    assert res.reasons == []
    assert bool(res) is True


def test_verify_rejects_dev_unsigned_even_with_its_key():
    """A dev-unsigned audit is rejected even when you hold the dev key —
    the key_id is blocklisted and key_source!='provided'."""
    m = _validated_manifest()
    audit = _audit_payload(m, DEV_UNSIGNED_KEY, key_source="dev-unsigned")
    res = verify_audit(audit, DEV_UNSIGNED_KEY)  # hmac would match...
    assert res.hmac_ok is True            # ...the HMAC is valid...
    assert res.accepted is False          # ...but the audit is NOT trusted.
    assert res.trusted is False
    # The dev-key fingerprint is blocklisted (this supersedes the generic
    # untrusted_source reason).
    assert any("dev_unsigned_key" in r for r in res.reasons)


def test_verify_rejects_tampered_manifest():
    m = _validated_manifest()
    audit = _audit_payload(m, _PROD_KEY)
    # Flip a verdict field after signing.
    audit["manifest"]["is_validated"] = True
    audit["manifest"]["verdict_level"] = "FAIL"  # mismatched with the signed bytes
    res = verify_audit(audit, _PROD_KEY)
    assert res.accepted is False
    assert any("hmac_mismatch" in r for r in res.reasons)


def test_verify_rejects_wrong_key():
    m = _validated_manifest()
    audit = _audit_payload(m, _PROD_KEY)
    other = b"a-different-but-valid-32-byte-key!!!!"
    res = verify_audit(audit, other)
    assert res.accepted is False
    assert res.hmac_ok is False


def test_verify_rejects_key_id_pin_mismatch():
    """Even with a valid HMAC, a verifier pinning a different key_id rejects."""
    m = _validated_manifest()
    audit = _audit_payload(m, _PROD_KEY)
    res = verify_audit(audit, _PROD_KEY, expected_key_id="0000000000000000")
    assert res.accepted is False
    assert any("key_id_mismatch" in r for r in res.reasons)


def test_verify_file_roundtrip(tmp_path):
    m = _validated_manifest()
    audit = _audit_payload(m, _PROD_KEY)
    p = tmp_path / "audit.json"
    p.write_text(json.dumps(audit), encoding="utf-8")
    res = verify_audit_file(p, _PROD_KEY)
    assert res.accepted is True
    assert res.manifest.case_id == "naca0012_airfoil"


def test_verify_cli_accept_and_reject(tmp_path):
    m = _validated_manifest()
    # trusted audit -> exit 0
    good = tmp_path / "good.json"
    good.write_text(json.dumps(_audit_payload(m, _PROD_KEY)), encoding="utf-8")
    assert verify_main([str(good), "--key", _PROD_KEY.decode()]) == 0
    # dev-unsigned audit -> exit 1 (rejected)
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(_audit_payload(m, DEV_UNSIGNED_KEY, "dev-unsigned")),
                   encoding="utf-8")
    assert verify_main([str(bad), "--key", DEV_UNSIGNED_KEY.decode()]) == 1
    # ...but --allow-untrusted accepts the dev audit on integrity alone
    # (HMAC intact), for dev/testing workflows.
    assert verify_main([str(bad), "--key", DEV_UNSIGNED_KEY.decode(),
                        "--allow-untrusted"]) == 0


def test_verify_missing_key_via_cli(tmp_path, monkeypatch):
    monkeypatch.delenv("CFD_HARNESS_SIGN_KEY", raising=False)
    p = tmp_path / "audit.json"
    p.write_text(json.dumps(_audit_payload(_validated_manifest(), _PROD_KEY)),
                 encoding="utf-8")
    assert verify_main([str(p)]) == 2  # no key -> usage error
