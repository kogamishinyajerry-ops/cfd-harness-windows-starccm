"""Mock-level tests for the vortex-street / run postprocess.json ingestion.

The vortex-street command reports only run markers in its JSON response and
writes the real residuals + force reports to <stem>_postprocess.json. These
tests pin the faithful ingestion (residuals as-is, forces flagged when the
report binding returns sentinel zeros) WITHOUT spawning STAR-CCM+.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from cfd_harness.executor.base import ExecutorStatus
from cfd_harness.starccm_adapter.executor import StarCCMExecutor


def _resp(data=None):
    return SimpleNamespace(
        ok=True, command="vortex-street(cyl.sim)", error=None,
        elapsed_s=10.6, data=data or {},
    )


def _write_pp(sim, payload):
    results = sim.parent / "Results"
    results.mkdir(parents=True, exist_ok=True)
    (results / f"{sim.stem}_postprocess.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )


def test_reads_real_residuals_and_flags_zero_forces(tmp_path):
    sim = tmp_path / "cyl.sim"
    sim.write_text("", encoding="utf-8")
    _write_pp(sim, {
        "monitors": {"items": [
            {"name": "Continuity", "type": "ResidualMonitor", "last": 1.03e-5},
            {"name": "X-momentum", "type": "ResidualMonitor", "last": 5.26e-6},
            {"name": "Energy", "type": "ResidualMonitor", "last": 0.039},
            {"name": "Physical Time", "type": "PhysicalTimeMonitor", "last": 1.0},
        ]},
        "drag_lift": {"part": "Cylinder", "Fx": 0.0, "Fy": 0.0, "Fz": 0.0, "ok": True},
        "ok": True,
    })
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    rep = ex._build_run_report(_resp({}), sim)

    assert rep.status == ExecutorStatus.OK
    res = rep.execution_result.residuals
    kq = rep.execution_result.key_quantities
    # Faithful: every ResidualMonitor, nothing else.
    assert res["Continuity"] == 1.03e-5
    assert res["Energy"] == 0.039           # reported as-is (will fail the floor)
    assert "Physical Time" not in res       # non-residual monitor excluded
    # Forces surfaced and flagged as sentinel zeros (DEC-005).
    assert kq["force_Fx"] == 0.0
    assert kq["force_reports_zero"] is True
    assert any("postprocess=read" in n for n in rep.notes)


def test_absent_postprocess_leaves_residuals_empty(tmp_path):
    sim = tmp_path / "cyl.sim"
    sim.write_text("", encoding="utf-8")
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    rep = ex._build_run_report(_resp({}), sim)
    assert rep.execution_result.residuals == {}
    assert any("postprocess=absent" in n for n in rep.notes)


def test_response_residuals_take_precedence(tmp_path):
    sim = tmp_path / "cyl.sim"
    sim.write_text("", encoding="utf-8")
    _write_pp(sim, {"monitors": {"items": [
        {"name": "Continuity", "type": "ResidualMonitor", "last": 9e-9}]}})
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    rep = ex._build_run_report(_resp({"residuals": {"p": 1e-7}}), sim)
    # Response already carried residuals → don't override from file.
    assert rep.execution_result.residuals == {"p": 1e-7}
