"""Verify a signed ``audit.json`` against a secret key + a trust policy.

This makes the DEC-010 "verifier policy" EXECUTABLE (previously it was only
a recipe string inside the audit). An audit is ACCEPTED only when:

  1. the HMAC verifies under the supplied key (integrity + authenticity),
  2. it was signed with a real key — ``key_source == "provided"`` and the
     key_id is NOT the well-known dev-unsigned fingerprint (trust), and
  3. if an ``expected_key_id`` is supplied, the audit's key_id matches it
     (so a verifier pins the exact production key).

Usage (CLI):
    CFD_HARNESS_SIGN_KEY=... python -m cfd_harness.audit_package.verify audit.json
    python -m cfd_harness.audit_package.verify audit.json --expect-key-id <id>
    python -m cfd_harness.audit_package.verify audit.json --allow-untrusted   # dev only

Exit code 0 = accepted, 1 = rejected, 2 = usage/IO error.
"""
from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from cfd_harness.audit_package.manifest import Manifest
from cfd_harness.audit_package.sign import (
    DEV_UNSIGNED_KEY_ID,
    Signature,
    key_fingerprint,
)

__all__ = ["VerifyResult", "verify_audit", "verify_audit_file"]

_SIGN_KEY_ENV = "CFD_HARNESS_SIGN_KEY"


@dataclass(frozen=True)
class VerifyResult:
    """The outcome of verifying one audit.json."""
    accepted: bool
    hmac_ok: bool
    trusted: bool
    key_id: str
    key_source: str
    reasons: List[str] = field(default_factory=list)
    manifest: Optional[Manifest] = None

    def __bool__(self) -> bool:
        return self.accepted


def verify_audit(
    audit: dict,
    key: bytes,
    *,
    expected_key_id: Optional[str] = None,
    require_trusted: bool = True,
) -> VerifyResult:
    """Verify a parsed audit dict (``{manifest, signature, signing, ...}``)."""
    reasons: List[str] = []

    try:
        manifest = Manifest(**audit["manifest"])
    except (KeyError, TypeError) as e:
        return VerifyResult(False, False, False, "", "unknown",
                            reasons=[f"malformed_manifest: {e}"])
    # Only feed Signature the fields it declares (forward-compatible if the
    # audit carries extra signature keys).
    sig_fields = {"digest", "hmac", "key_id", "algorithm", "signed_at"}
    sig_data = {k: v for k, v in audit.get("signature", {}).items() if k in sig_fields}
    try:
        sig = Signature(**sig_data)
    except TypeError as e:
        return VerifyResult(False, False, False, "", "unknown",
                            reasons=[f"malformed_signature: {e}"], manifest=manifest)

    signing = audit.get("signing", {}) or {}
    key_source = signing.get("key_source", "unknown")

    hmac_ok = sig.verify(manifest, key)
    if not hmac_ok:
        reasons.append("hmac_mismatch: signature does not verify under the supplied key")

    # Trust policy. Only enforced when require_trusted=True; with
    # require_trusted=False (--allow-untrusted) the verifier reports
    # INTEGRITY ONLY — useful for checking a dev audit wasn't corrupted —
    # while still surfacing trusted=False.
    is_dev = sig.key_id == DEV_UNSIGNED_KEY_ID
    trusted = (key_source == "provided") and not is_dev
    if require_trusted:
        if is_dev:
            reasons.append("dev_unsigned_key: signed with the DEV-UNSIGNED key (never trust)")
        elif key_source != "provided":
            reasons.append(f"untrusted_source: key_source={key_source!r} (expected 'provided')")

    # A pinned key_id mismatch is ALWAYS disqualifying, even with --allow-untrusted.
    if expected_key_id is not None and sig.key_id != expected_key_id:
        reasons.append(f"key_id_mismatch: {sig.key_id!r} != expected {expected_key_id!r}")

    accepted = hmac_ok and not reasons
    return VerifyResult(
        accepted=accepted,
        hmac_ok=hmac_ok,
        trusted=trusted,
        key_id=sig.key_id,
        key_source=key_source,
        reasons=reasons,
        manifest=manifest,
    )


def verify_audit_file(
    path,
    key: bytes,
    *,
    expected_key_id: Optional[str] = None,
    require_trusted: bool = True,
) -> VerifyResult:
    """Load an audit.json from ``path`` and verify it."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return verify_audit(
        data, key, expected_key_id=expected_key_id, require_trusted=require_trusted
    )


def _main(argv: Optional[list] = None) -> int:
    import argparse

    p = argparse.ArgumentParser(
        prog="cfd-harness-verify-audit",
        description="Verify a signed audit.json (DEC-010 trust policy).",
    )
    p.add_argument("audit", help="path to audit.json")
    p.add_argument("--key", default=None,
                   help=f"HMAC key (prefer the {_SIGN_KEY_ENV} env var)")
    p.add_argument("--expect-key-id", default=None,
                   help="require the audit's signature.key_id to equal this")
    p.add_argument("--allow-untrusted", action="store_true",
                   help="do not reject dev-unsigned audits (dev/testing only)")
    args = p.parse_args(argv)

    key_str = args.key or os.environ.get(_SIGN_KEY_ENV)
    if not key_str:
        print(f"[verify][error] no key: pass --key or set {_SIGN_KEY_ENV}", file=sys.stderr)
        return 2
    try:
        result = verify_audit_file(
            args.audit, key_str.encode("utf-8"),
            expected_key_id=args.expect_key_id,
            require_trusted=not args.allow_untrusted,
        )
    except (OSError, json.JSONDecodeError) as e:
        print(f"[verify][error] cannot read audit: {e}", file=sys.stderr)
        return 2

    verdict = "ACCEPTED" if result.accepted else "REJECTED"
    print(f"[verify] {verdict} key_id={result.key_id} key_source={result.key_source} "
          f"hmac_ok={result.hmac_ok} trusted={result.trusted}")
    for r in result.reasons:
        print(f"  - {r}")
    return 0 if result.accepted else 1


if __name__ == "__main__":
    raise SystemExit(_main())
