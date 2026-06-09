"""Serialize: stable byte representation of a Manifest.

Two manifests with the same fields MUST serialize to identical bytes
(sorted keys, deterministic separators). This is what makes
signatures reproducible.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from cfd_harness.audit_package.manifest import Manifest

__all__ = ["serialize_manifest", "manifest_to_canonical_dict"]


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
    """Stable byte representation. Sorted keys, no trailing whitespace."""
    canonical = manifest_to_canonical_dict(manifest)
    return json.dumps(
        canonical,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
