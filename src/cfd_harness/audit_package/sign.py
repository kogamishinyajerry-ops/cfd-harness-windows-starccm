"""Signer: HMAC-SHA-256 over the canonical manifest bytes.

`byte-deterministic signed audit package` is one of the project's five
ground rules. The signer takes a Manifest, serializes it via
``serialize_manifest``, binds the signing timestamp into the payload, and
HMAC-signs the bytes. The resulting ``Signature`` is stored alongside the
manifest.

Trust model (hardened 2026-06-13, see DEC-010):
  - The HMAC is only as trustworthy as the KEY SECRECY. A signature proves
    authenticity *only* to a verifier holding the same secret key.
  - ``Signature.key_id`` is a non-secret fingerprint of the signing key. It
    lets a verifier (a) know which key to expect and (b) reject audits
    signed with the well-known DEV-UNSIGNED key — without revealing the key.
    ``verify`` requires the recomputed fingerprint of the supplied key to
    match, so an audit signed with key A never verifies against key B.
  - ``signed_at`` is bound INTO the signed payload (a separator + the ISO
    timestamp is appended before hashing), so the timestamp cannot be
    backdated without breaking the signature.
  - Keys must be >= ``MIN_KEY_BYTES`` (256 bits). There is NO hardcoded
    production key; the CLI sources the key from ``--sign-key`` or the
    ``CFD_HARNESS_SIGN_KEY`` env var, and falls back to an explicitly
    untrusted, labelled dev key only with a loud warning.
"""
from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

from cfd_harness.audit_package.manifest import Manifest
from cfd_harness.audit_package.serialize import serialize_manifest

__all__ = ["Signer", "Signature", "key_fingerprint", "MIN_KEY_BYTES"]

# Minimum HMAC key length. HMAC-SHA-256 keys shorter than the block/output
# size weaken security and invite offline brute-force of captured audits.
MIN_KEY_BYTES = 32

# Unit separator: binds ``signed_at`` into the signed payload so the
# timestamp is authenticated (not backdatable). Chosen because it cannot
# appear in the JSON manifest bytes that precede it.
_TS_SEP = b"\x1f"

# Salt for the key fingerprint. Versioned so a future fingerprint scheme
# change is distinguishable. The fingerprint is one-way (a SHA-256 prefix)
# and never reveals the key.
_KEYID_SALT = b"cfd-harness-keyid:v1:"


def key_fingerprint(key: bytes) -> str:
    """A non-secret, stable fingerprint of an HMAC key.

    Lets a verifier tell which key signed an audit (and blocklist the
    DEV-UNSIGNED key) without knowing the key itself. NOT reversible.
    """
    return hashlib.sha256(_KEYID_SALT + key).hexdigest()[:16]


@dataclass(frozen=True)
class Signature:
    """An HMAC-SHA-256 signature over a serialized Manifest + timestamp."""
    digest: str          # hex SHA-256 of the signed payload (convenience checksum only)
    hmac: str            # hex HMAC-SHA-256 — the actual authentication token
    key_id: str = ""     # non-secret fingerprint of the signing key (see key_fingerprint)
    algorithm: str = "HMAC-SHA-256"
    signed_at: str = ""  # ISO-8601; bound into the HMAC payload (authenticated)

    def _payload(self, manifest: Manifest) -> bytes:
        # The signed bytes are the canonical manifest followed by the
        # timestamp, so altering signed_at breaks the signature.
        return serialize_manifest(manifest) + _TS_SEP + self.signed_at.encode("utf-8")

    def verify(self, manifest: Manifest, key: bytes) -> bool:
        """Recompute the signature and compare (constant-time).

        Returns True iff the digest, the HMAC, AND the key fingerprint all
        match. The key_id check means a signature made with one key can
        never verify against a different key, and a verifier can detect a
        DEV-UNSIGNED audit by its key_id alone.
        """
        payload = self._payload(manifest)
        expected_digest = hashlib.sha256(payload).hexdigest()
        expected_hmac = hmac.new(key, payload, hashlib.sha256).hexdigest()
        expected_key_id = key_fingerprint(key)
        return (
            hmac.compare_digest(self.digest, expected_digest)
            and hmac.compare_digest(self.hmac, expected_hmac)
            and hmac.compare_digest(self.key_id, expected_key_id)
        )


class Signer:
    """Sign Manifest objects with an HMAC key."""
    def __init__(self, key: bytes) -> None:
        if len(key) < MIN_KEY_BYTES:
            raise ValueError(
                f"HMAC key must be at least {MIN_KEY_BYTES} bytes (256 bits); "
                f"got {len(key)}. Generate one with "
                f"`python -c \"import secrets;print(secrets.token_hex(32))\"`."
            )
        self.key = key
        self.key_id = key_fingerprint(key)

    def sign(self, manifest: Manifest) -> Signature:
        from datetime import datetime, timezone
        signed_at = datetime.now(timezone.utc).isoformat()
        payload = serialize_manifest(manifest) + _TS_SEP + signed_at.encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        sig = hmac.new(self.key, payload, hashlib.sha256).hexdigest()
        return Signature(
            digest=digest,
            hmac=sig,
            key_id=self.key_id,
            signed_at=signed_at,
        )
