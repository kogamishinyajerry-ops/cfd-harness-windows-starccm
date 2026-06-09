"""Tests for the orchestrator's skill_loader."""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_harness.orchestrator.skill_loader import (
    get_categories,
    get_skill,
    load_skills_by_type,
    skill_source_exists,
)


def test_load_skills_by_type_prompt():
    """Loading all `prompt` skills returns the model_routing + cfd_harness
    + architecture prompt skills."""
    skills = load_skills_by_type(solver_type="prompt")
    assert all(s.get("type") == "prompt" for s in skills)
    # We have at least: subagent_priority, dec_scope_driven,
    # four_question_gate, tolerance_integrity, four_plane_law, mock_first
    skill_ids = {s.get("skill_id") for s in skills}
    assert "subagent_priority" in skill_ids
    assert "tolerance_integrity" in skill_ids


def test_load_skills_by_type_harness():
    skills = load_skills_by_type(solver_type="harness")
    assert all(s.get("type") == "harness" for s in skills)
    skill_ids = {s.get("skill_id") for s in skills}
    assert "byte_deterministic_audit" in skill_ids
    # Stage 3+ skills are present but flagged with stage
    assert "mesh_pipeline" in skill_ids
    assert "codebuddy_repl" in skill_ids


def test_load_skills_by_category():
    starccm_skills = load_skills_by_type(category="starccm")
    assert len(starccm_skills) == 4   # mesh / solve / postprocess / codebuddy_repl
    assert all(s.get("category") == "starccm" for s in starccm_skills)


def test_load_skills_by_type_and_category():
    """Both filters must apply (intersection)."""
    skills = load_skills_by_type(solver_type="harness", category="starccm")
    assert all(s.get("type") == "harness" and s.get("category") == "starccm" for s in skills)


def test_invalid_solver_type_raises():
    with pytest.raises(ValueError, match="Invalid solver_type"):
        load_skills_by_type(solver_type="bogus")


def test_unknown_category_returns_empty():
    skills = load_skills_by_type(category="nonexistent")
    assert skills == []


def test_get_categories():
    cats = get_categories()
    assert set(cats) == {"model_routing", "cfd_harness", "starccm", "architecture"}


def test_get_skill_found():
    s = get_skill("subagent_priority", "model_routing")
    assert s is not None
    assert s.get("skill_id") == "subagent_priority"


def test_get_skill_missing():
    s = get_skill("nonexistent", "model_routing")
    assert s is None


def test_skill_source_exists_for_real_prompt():
    s = get_skill("subagent_priority", "model_routing")
    # Source is `~/.mavis/AGENTS.md`; we may or may not have it in CI.
    # The test asserts the API is callable and returns a bool.
    result = skill_source_exists(s)
    assert isinstance(result, bool)
