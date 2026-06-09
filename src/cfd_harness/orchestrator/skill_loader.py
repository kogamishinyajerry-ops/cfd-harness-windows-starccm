"""Skill loader: enumerate the chief engineer's available skills.

Solver-agnostic. Loads ``knowledge/skill_index.yaml`` and provides
filter-by-category and filter-by-solver_type views.

The skill loader is the bridge between the chief engineer's
prompt-level decisions and the actual Python skills under
``cfd_harness.starccm_adapter.*`` (Stage 3+) and the user's
``D:\\StarCCM Codebuddy`` REPL. It is NOT an executor itself; it's
a registry.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict

import yaml

__all__ = [
    "SkillEntry",
    "load_skills_by_type",
    "get_categories",
    "get_skill",
    "skill_source_exists",
]


class SkillEntry(TypedDict, total=False):
    """A single skill entry from the index."""
    skill_id: str
    category: str
    name: str
    description: str
    type: str                # "prompt" | "harness"
    source_path: str


# Canonical path to the skill index — `knowledge/skill_index.yaml`.
_INDEX_PATH = Path(__file__).resolve().parent.parent.parent.parent / "knowledge" / "skill_index.yaml"


def _resolve_path(source_path: str) -> Path:
    return Path(source_path).expanduser()


def _load_index(index_path: Optional[Path] = None) -> Dict[str, Any]:
    path = _INDEX_PATH if index_path is None else index_path
    if not path.exists():
        # The skill index is a Stage 2+ artifact; for Stage 1+2 with
        # no skill_index.yaml, return an empty index so callers can
        # bootstrap without an error.
        return {"by_category": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"by_category": {}}


def _category_view(index: Dict[str, Any]) -> Dict[str, Any]:
    return index.get("by_category", index)


def _solver_type_view(index: Dict[str, Any]) -> Dict[str, Any]:
    by_type = index.get("by_solver_type")
    if by_type is not None:
        return by_type
    derived: Dict[str, Any] = {}
    for category, payload in _category_view(index).items():
        for skill_id, skill_def in payload.get("skills", {}).items():
            skill_type = skill_def.get("type", "")
            bucket = derived.setdefault(
                skill_type,
                {"description": f"Skills grouped by type={skill_type}", "skills": {}},
            )
            bucket["skills"][f"{category}.{skill_id}"] = {
                "category": category,
                "skill_id": skill_id,
                "name": skill_def.get("name", ""),
                "description": skill_def.get("description", ""),
                "type": skill_type,
                "source_path": skill_def.get("source_path", ""),
            }
    return derived


def _build_entry(category: str, skill_id: str, skill_def: Dict[str, Any]) -> SkillEntry:
    return SkillEntry(
        skill_id=skill_id,
        category=category,
        name=skill_def.get("name", ""),
        description=skill_def.get("description", ""),
        type=skill_def.get("type", ""),
        source_path=skill_def.get("source_path", ""),
    )


def load_skills_by_type(
    solver_type: Optional[str] = None,
    category: Optional[str] = None,
    index_path: Optional[Path] = None,
) -> List[SkillEntry]:
    """Load skills filtered by solver_type (prompt/harness) and/or category.

    Returns an empty list if the skill index is missing (Stage 1+2
    behavior).
    """
    VALID_TYPES = {"prompt", "harness"}

    if solver_type is not None and solver_type not in VALID_TYPES:
        raise ValueError(
            f"Invalid solver_type={solver_type!r}. Expected one of: {sorted(VALID_TYPES)}"
        )

    idx = _load_index(index_path=index_path)
    by_category = _category_view(idx)
    by_solver_type = _solver_type_view(idx)
    results: List[SkillEntry] = []

    if solver_type is not None and category is None:
        type_bucket = by_solver_type.get(solver_type, {})
        for entry_key in sorted(type_bucket.get("skills", {})):
            skill_def = type_bucket["skills"][entry_key]
            results.append(
                _build_entry(
                    category=skill_def.get("category", ""),
                    skill_id=skill_def.get("skill_id", entry_key),
                    skill_def=skill_def,
                )
            )
        return results

    categories_to_scan = [category] if category is not None else sorted(by_category)
    for cat_key in categories_to_scan:
        cat = by_category.get(cat_key, {})
        skills = cat.get("skills", {})
        for skill_id in sorted(skills):
            skill_def = skills[skill_id]
            skill_type = skill_def.get("type")
            if solver_type is not None and skill_type != solver_type:
                continue
            results.append(_build_entry(category=cat_key, skill_id=skill_id, skill_def=skill_def))
    return results


def get_categories() -> List[str]:
    return sorted(_category_view(_load_index()).keys())


def get_skill(skill_id: str, category: str) -> Optional[SkillEntry]:
    idx = _category_view(_load_index())
    cat = idx.get(category, {})
    skills = cat.get("skills", {})
    skill_def = skills.get(skill_id)
    if skill_def is None:
        return None
    return _build_entry(category=category, skill_id=skill_id, skill_def=skill_def)


def skill_source_exists(skill: SkillEntry) -> bool:
    source = skill.get("source_path", "")
    if not source:
        return False
    return _resolve_path(source).expanduser().exists()
