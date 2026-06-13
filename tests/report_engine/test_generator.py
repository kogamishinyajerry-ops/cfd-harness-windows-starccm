"""Tests for the V&V markdown report generator.

Pins the per-quantity rendering: the comparator already computes
measured/gold/relative_error per quantity, and the report must show those
real numbers (not em-dashes), with a graceful fallback for older data.json.
"""
from __future__ import annotations

import json

from cfd_harness.report_engine.generator import ReportGenerator, _fmt_num, _fmt_pct


def _payload(comparison_quantities):
    return {
        "task_spec": {"case_id": "naca0012_airfoil"},
        "run_report": {
            "mode": "win_starccm",
            "contract_hash": "abc123def456",
            "version": "0.3",
            "notes": ["win_starccm_real_bridge_stage3plus"],
            "execution_result": {"is_mock": False, "residuals": {"U": 1e-7}},
        },
        "verifier_report": {
            "level": "WARN",
            "is_validated": False,
            "comparison_all_pass": False,
            "comparison_failing": ["cd"],
            "comparison_quantities": comparison_quantities,
            "convergence_all_pass": True,
            "convergence_failing": [],
            "physics_all_pass": True,
            "physics_failures": [],
            "suggestions": [],
        },
    }


def test_fmt_helpers():
    assert _fmt_pct(0.04) == "4.00%"
    assert _fmt_pct(None) == "—"
    assert _fmt_pct(float("inf")) == "—"
    assert _fmt_num(0.2356789) == "0.2357"
    assert _fmt_num(float("nan")) == "—"
    assert _fmt_num(None) == "—"


def test_report_renders_per_quantity_numbers(tmp_path):
    q = [
        {"name": "cl", "measured": 0.235, "gold": 0.24, "relative_error": 0.0208,
         "tolerance": 0.05, "all_pass": True},
        {"name": "cd", "measured": 0.01, "gold": 0.006, "relative_error": 0.6667,
         "tolerance": 0.1, "all_pass": False},
    ]
    p = tmp_path / "data.json"
    p.write_text(json.dumps(_payload(q)), encoding="utf-8")
    md = ReportGenerator().render(p)

    # Real numbers are rendered, not em-dashes.
    assert "0.235" in md and "0.24" in md
    assert "2.08%" in md    # cl relative error
    assert "66.67%" in md   # cd relative error
    assert "`cl`" in md and "`cd`" in md
    # Pass/fail glyphs both present.
    assert "✅" in md and "❌" in md
    # The measured-vs-gold rows are no longer all em-dashes.
    assert "| — | — |" not in md


def test_report_falls_back_to_names_without_quantities(tmp_path):
    # Older data.json without comparison_quantities -> name-only fallback.
    p = tmp_path / "data.json"
    p.write_text(json.dumps(_payload([])), encoding="utf-8")
    md = ReportGenerator().render(p)
    assert "`cd`" in md      # the failing quantity name still appears
    assert "—" in md         # with em-dash placeholders
