"""Orchestrator: solver-agnostic dispatcher for the multi-agent crew.

Plane: EXECUTION. Provides the `skill_loader` — the chief engineer
uses this to enumerate available "skills" (eg. mesh, solve, postprocess)
by category or by solver type. The skill loader does NOT know about
specific solver commands; the actual command invocations live in
the `starccm_adapter` (Stage 3+) or are scripted in `bin/` /
`scripts/`.
"""
from cfd_harness.orchestrator.skill_loader import (
    SkillEntry,
    get_categories,
    get_skill,
    load_skills_by_type,
    skill_source_exists,
)

__all__ = [
    "SkillEntry",
    "load_skills_by_type",
    "get_categories",
    "get_skill",
    "skill_source_exists",
]
