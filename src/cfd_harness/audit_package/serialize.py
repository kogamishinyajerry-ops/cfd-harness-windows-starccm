"""Serialize: stable byte representation of a Manifest.

Two manifests with the same fields MUST serialize to identical bytes
(sorted keys, deterministic separators). This is what makes
signatures reproducible.
"""
from __future__ import annotations

import json
import unicodedata
from typing import Any, Dict

from cfd_harness.audit_package.manifest import Manifest

__all__ = ["serialize_manifest", "manifest_to_canonical_dict"]


def _nfc(value: Any) -> Any:
    """Recursively NFC-normalize strings so semantically-identical text
    signs to identical bytes regardless of the platform's Unicode form
    (e.g. macOS NFD paths vs Linux NFC). Without this, an untampered
    manifest could raise a false tamper alarm across machines.
    """
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_nfc(v) for v in value]
    if isinstance(value, dict):
        return {k: _nfc(v) for k, v in value.items()}
    return value


def manifest_to_canonical_dict(manifest: Manifest) -> Dict[str, Any]:
    """Project a Manifest to a JSON-serializable dict with stable key order."""
    return {
        "schema_version": manifest.schema_version,
        "case_id": manifest.case_id,
        "executor_mode": manifest.executor_mode,
        "contract_hash": manifest.contract_hash,
        "spec_version": manifest.spec_version,
        "verdict_level": manifest.verdict_level,
        "is_validated": manifest.is_validated,
        "is_mock": manifest.is_mock,
        "comparison_all_pass": manifest.comparison_all_pass,
        "comparison_failing": sorted(manifest.comparison_failing),
        "convergence_all_pass": manifest.convergence_all_pass,
        "convergence_failing": sorted(manifest.convergence_failing),
        "physics_all_pass": manifest.physics_all_pass,
        "suggestions": sorted(
            ({"category": s["category"], "severity": s["severity"], "message": s["message"]}
             for s in manifest.suggestions),
            key=lambda s: (s["category"], s["severity"], s["message"]),
        ),
        "gold_anchor": manifest.gold_anchor,
        "solver_profile": manifest.solver_profile,
    }


def serialize_manifest(manifest: Manifest) -> bytes:
    """Stable byte representation. Sorted keys, no trailing whitespace,
    NFC-normalized strings, and NO non-standard JSON tokens.

    ``allow_nan=False`` makes a stray ``nan``/``inf`` raise ``ValueError``
    instead of emitting non-RFC-8259 ``NaN``/``Infinity`` tokens that
    different verifiers parse differently (a non-determinism / false-tamper
    hazard).
    """
    canonical = _nfc(manifest_to_canonical_dict(manifest))
    return json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
