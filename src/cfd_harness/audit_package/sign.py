"""Signer: HMAC-SHA-256 over the canonical manifest bytes.

`byte-deterministic signed audit package` is one of the project's
five ground rules. The signer takes a Manifest, serializes it via
`serialize_manifest`, and signs the bytes with an HMAC key. The
resulting `Signature` is what gets stored alongside the manifest.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from cfd_harness.audit_package.manifest import Manifest
from cfd_harness.audit_package.serialize import serialize_manifest

__all__ = ["Signer", "Signature"]


@dataclass(frozen=True)
class Signature:
    """An HMAC-SHA-256 signature over a serialized Manifest."""
    digest: str          # hex SHA-256 of the serialized manifest
    hmac: str            # hex HMAC-SHA-256
    algorithm: str = "HMAC-SHA-256"
    signed_at: str = ""  # ISO-8601 timestamp (set by Signer.sign)

    def verify(self, manifest: Manifest, key: bytes) -> bool:
        """Recompute the signature and compare; constant-time compare."""
        payload = serialize_manifest(manifest)
        expected_digest = hashlib.sha256(payload).hexdigest()
        expected_hmac = hmac.new(key, payload, hashlib.sha256).hexdigest()
        return (
            hmac.compare_digest(self.digest, expected_digest)
            and hmac.compare_digest(self.hmac, expected_hmac)
        )


class Signer:
    """Sign and verify Manifest objects with an HMAC key."""
    def __init__(self, key: bytes) -> None:
        if not key:
            raise ValueError("HMAC key must be non-empty bytes")
        self.key = key

    def sign(self, manifest: Manifest) -> Signature:
        from datetime import datetime, timezone
        payload = serialize_manifest(manifest)
        digest = hashlib.sha256(payload).hexdigest()
        sig = hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        return Signature(
            digest=digest,
            hmac=sig,
            signed_at=datetime.now(timezone.utc).isoformat(),
        )
