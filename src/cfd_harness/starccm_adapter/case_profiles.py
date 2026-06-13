"""
Case profile validator — ensures case_profiles.yaml is complete and self-consistent.

All 16 cases (3 anchor + 13 mock-only) + 4 rotor-family profiles must be loadable
and structurally valid. This module is used by the smoke test and CI.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import yaml


CASE_PROFILES_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..",
    "knowledge", "case_profiles.yaml",
)


def load_profiles(path: Optional[str] = None) -> Dict:
    """Load case_profiles.yaml and return the parsed dict."""
    path = path or CASE_PROFILES_PATH
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def validate_profiles(path: Optional[str] = None) -> Dict[str, List[str]]:
    """Validate all case profiles and return {case_id: [errors]}.

    An empty errors list means the profile is valid.
    """
    path = path or CASE_PROFILES_PATH
    data = load_profiles(path)

    errors: Dict[str, List[str]] = {}
    profiles = data.get("profiles", {})

    required_fields = ["status", "sim_path", "macros", "expected_outputs"]
    valid_statuses = {"wired", "mock_only", "mock_validated", "real_validated", "deferred"}

    for case_id, profile in profiles.items():
        case_errors: List[str] = []

        # Required fields
        for field in required_fields:
            if field not in profile:
                case_errors.append(f"missing required field: {field}")

        # Status validation
        status = profile.get("status", "")
        if status not in valid_statuses:
            case_errors.append(
                f"invalid status '{status}' (valid: {valid_statuses})"
            )

        # Wired cases must have sim_path
        if status == "wired" and profile.get("sim_path") is None:
            case_errors.append(
                "status=wired requires non-null sim_path"
            )

        # macros must be list
        macros = profile.get("macros", [])
        if not isinstance(macros, list):
            case_errors.append("macros must be a list")

        # expected_outputs must be list
        outputs = profile.get("expected_outputs", [])
        if not isinstance(outputs, list) or len(outputs) == 0:
            case_errors.append("expected_outputs must be a non-empty list")

        if case_errors:
            errors[case_id] = case_errors

    return errors


def get_case_list(path: Optional[str] = None) -> List[str]:
    """Return all case IDs from case_profiles.yaml."""
    data = load_profiles(path)
    return list(data.get("profiles", {}).keys())


def get_cases_by_status(status: str, path: Optional[str] = None) -> List[str]:
    """Return case IDs filtered by status."""
    data = load_profiles(path)
    return [
        case_id for case_id, p in data.get("profiles", {}).items()
        if p.get("status") == status
    ]


def count_cases(path: Optional[str] = None) -> Dict[str, int]:
    """Count cases by status."""
    data = load_profiles(path)
    counts: Dict[str, int] = {}
    for p in data.get("profiles", {}).values():
        s = p.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts
