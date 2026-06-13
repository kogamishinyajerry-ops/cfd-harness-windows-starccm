"""Audit package: signed manifest for V&V audit trail.

Plane: AUDIT. MAY import EXECUTION + VERIFICATION + REPORTING + METRICS.

The audit package is the project's credibility anchor — every
benchmark run gets a SHA-256 over `(spec_hash | executor_mode |
executor_version)`, plus an HMAC signature over the manifest fields.
The signed manifest is what the chief engineer cites in a
stage-exit-gate claim.
"""
from cfd_harness.audit_package.manifest import Manifest, ManifestBuilder
from cfd_harness.audit_package.sign import Signer, Signature, key_fingerprint
from cfd_harness.audit_package.serialize import serialize_manifest

# NOTE: the verifier lives in cfd_harness.audit_package.verify and is NOT
# re-exported here on purpose — it is runnable via `python -m
# cfd_harness.audit_package.verify`, and re-importing it in this __init__
# triggers a runpy double-import RuntimeWarning. Import it directly:
#   from cfd_harness.audit_package.verify import verify_audit_file

__all__ = [
    "Manifest",
    "ManifestBuilder",
    "Signer",
    "Signature",
    "key_fingerprint",
    "serialize_manifest",
]
