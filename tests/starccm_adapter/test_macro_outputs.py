"""Mock-level tests for StarCCMExecutor._build_macro_run_report.

These exercise the summary.json parse + fail-closed plausibility gate
WITHOUT spawning STAR-CCM+ (we feed a fabricated CodebuddyResponse and a
hand-written summary.json on disk). They are the first unit coverage of the
adapter's output-parsing path (previously only the bridge had unit tests).

Closes part of the takeover-recon gap "adapter parse path has no mock test"
and guards the DEC-005 fail-closed behaviour: a macro that reports
run_ok=true while emitting a sentinel Cl/Cd must NOT be reported as a
successful execution.
"""
from __future__ import annotations

import json
from types import SimpleNamespace

from cfd_harness.executor.base import ExecutorStatus
from cfd_harness.models import FlowType, GeometryType, TaskSpec
from cfd_harness.starccm_adapter.executor import StarCCMExecutor


def _naca_spec() -> TaskSpec:
    return TaskSpec(
        case_id="naca0012_airfoil",
        flow_type=FlowType.EXTERNAL,
        geometry_type=GeometryType.IMPORTED_GEOMETRY,
    )


def _write_summary(codebuddy_root, payload: dict) -> None:
    results = codebuddy_root / "Cases" / "Results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "naca2412_summary.json").write_text(json.dumps(payload), encoding="utf-8")


def _fake_ok_resp() -> SimpleNamespace:
    # Mimics a CodebuddyResponse for a successful spawn (RC=0).
    return SimpleNamespace(
        ok=True,
        command="run_macro(NacaTrueE2E.java)",
        error=None,
        elapsed_s=12.3,
        data={"macro_path": "NacaTrueE2E.java"},
    )


def test_implausible_force_coeffs_fail_closed(tmp_path):
    """run_ok=true with a sentinel Cl=8.52 / Cd=-0.41 must NOT be success."""
    _write_summary(tmp_path, {"run_ok": True, "init_ok": True, "Cl": 8.52, "Cd": -0.41})
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    report = ex._build_macro_run_report(_fake_ok_resp(), tmp_path / "x.sim", _naca_spec())

    assert report.status == ExecutorStatus.OK  # the spawn itself completed
    res = report.execution_result
    assert res is not None
    assert res.success is False, "implausible coefficients must fail closed"
    kq = res.key_quantities
    assert kq["_macro_summary"]["plausible"] is False
    assert "implausible_reasons" in kq["_macro_summary"]
    # Implausible coefficients are quarantined, NOT surfaced for comparison.
    assert "force_coefficients" not in kq
    assert kq["force_coefficients_quarantined"]["cl"] == 8.52
    assert any("summary_plausible=False" in n for n in report.notes)


def test_run_ok_false_fail_closed(tmp_path):
    """run_ok=false must fail closed even with no coefficients reported."""
    _write_summary(tmp_path, {"run_ok": False, "init_ok": True})
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    report = ex._build_macro_run_report(_fake_ok_resp(), tmp_path / "x.sim", _naca_spec())

    res = report.execution_result
    assert res.success is False
    assert res.key_quantities["_macro_summary"]["plausible"] is False
    assert "run_ok=false" in res.key_quantities["_macro_summary"]["implausible_reasons"]


def test_u_centerline_not_vetoed_by_implausible_coeffs(tmp_path):
    """An independent, valid u_centerline must NOT be failed by an implausible
    force coefficient — the bad coefficient is quarantined, not a veto. (Guards
    the decoupling: only run_ok=false vetoes everything.)"""
    results = tmp_path / "Cases" / "Results"
    results.mkdir(parents=True, exist_ok=True)
    (results / "naca2412_summary.json").write_text(
        json.dumps({"run_ok": True, "Cl": 8.52, "Cd": -0.41}), encoding="utf-8")
    (results / "naca2412_u_centerline.csv").write_text(
        "y,u\n0.0,0.0\n0.5,0.3\n1.0,1.0\n", encoding="utf-8")
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    report = ex._build_macro_run_report(_fake_ok_resp(), tmp_path / "x.sim", _naca_spec())

    res = report.execution_result
    assert res.success is True, "valid u_centerline must survive a bad coefficient"
    assert res.key_quantities["u_centerline"] == [0.0, 0.3, 1.0]
    # ...but the implausible coefficient is still quarantined, never surfaced.
    assert "force_coefficients_quarantined" in res.key_quantities
    assert "force_coefficients" not in res.key_quantities
    assert res.key_quantities["_macro_summary"]["plausible"] is False


def test_plausible_force_coeffs_pass(tmp_path):
    """A physically sane Cl/Cd is surfaced for V&V and counts as success."""
    _write_summary(tmp_path, {"run_ok": True, "init_ok": True, "Cl": 0.235, "Cd": 0.0061})
    ex = StarCCMExecutor(codebuddy_path=str(tmp_path))
    report = ex._build_macro_run_report(_fake_ok_resp(), tmp_path / "x.sim", _naca_spec())

    res = report.execution_result
    assert res.success is True
    assert res.key_quantities["_macro_summary"]["plausible"] is True
    assert res.key_quantities["force_coefficients"]["cl"] == 0.235
    assert "force_coefficients_quarantined" not in res.key_quantities
