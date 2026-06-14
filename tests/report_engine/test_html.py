"""Tests for the self-contained HTML V&V report generator."""
from __future__ import annotations

import json

from cfd_harness.report_engine.html import render_html_report, residual_svg


def _data(tmp_path, **ver):
    base_ver = {
        "level": "FAIL", "is_validated": False, "comparison_all_pass": False,
        "comparison_failing": ["strouhal_number", "cd_mean"],
        "comparison_quantities": [], "convergence_all_pass": False,
        "convergence_failing": ["Energy"], "physics_all_pass": True,
    }
    base_ver.update(ver)
    payload = {
        "task_spec": {"case_id": "circular_cylinder_wake"},
        "run_report": {
            "mode": "win_starccm", "notes": ["postprocess=read(residuals=7)"],
            "execution_result": {"is_mock": False,
                                  "residuals": {"Continuity": 1.0e-5, "Energy": 0.039}},
        },
        "verifier_report": base_ver,
    }
    p = tmp_path / "data.json"
    p.write_text(json.dumps(payload), encoding="utf-8")
    return p


def test_residual_svg_renders_lines_and_floor():
    svg = residual_svg(
        list(range(1, 101)),
        {"Continuity": [10 ** (-i / 20) for i in range(100)],
         "Energy": [0.04] * 100},
        floor=1e-4,
    )
    assert svg.startswith("<svg")
    assert "polyline" in svg
    assert "收敛阈值" in svg          # the floor line label
    assert "Continuity" in svg and "Energy" in svg


def test_render_writes_self_contained_html(tmp_path):
    out = render_html_report(_data(tmp_path))
    assert out.exists()
    html = out.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "circular_cylinder_wake" in html
    assert "FAIL" in html
    assert "未验证" in html               # not-validated badge (Chinese)
    # V&V table shows the un-measurable gold quantities.
    assert "strouhal_number" in html and "未测得" in html
    # residual table.
    assert "Continuity" in html and "Energy" in html
    # No external assets / scripts.
    assert "<script" not in html
    assert "http://" not in html and "https://" not in html


def test_render_flags_quiescent_fields(tmp_path):
    """A zero-flow run (force_reports_zero) must warn that the cloud plots
    carry no real field data — not present blank contours as results."""
    p = _data(tmp_path)
    d = json.loads(p.read_text(encoding="utf-8"))
    d["run_report"]["execution_result"]["key_quantities"] = {"force_reports_zero": True}
    p.write_text(json.dumps(d), encoding="utf-8")
    html = render_html_report(p).read_text(encoding="utf-8")
    assert "无有效流动数据" in html
    assert "Select Function" in html


def test_render_embeds_convergence_and_png(tmp_path):
    # convergence.json with a residual history
    conv = tmp_path / "conv.json"
    conv.write_text(json.dumps({
        "iterations": list(range(1, 51)),
        "residuals": {"Continuity": [10 ** (-i / 10) for i in range(50)]},
    }), encoding="utf-8")
    # a "png" (content isn't validated — only read + base64-embedded)
    png = tmp_path / "vorticity.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\nFAKEPNGBYTES")
    # an audit.json
    audit = tmp_path / "audit.json"
    audit.write_text(json.dumps({
        "signature": {"key_id": "abc123", "hmac": "deadbeef" * 8,
                      "algorithm": "HMAC-SHA-256", "signed_at": "2026-06-14T00:00:00Z"},
        "signing": {"key_source": "provided", "trusted": True},
    }), encoding="utf-8")

    out = render_html_report(
        _data(tmp_path), convergence_json=conv,
        scene_pngs=[(str(png), "涡量 vorticity")], audit_json=str(audit),
        out_html=str(tmp_path / "report.html"),
    )
    html = out.read_text(encoding="utf-8")
    assert "<svg" in html                                  # convergence plot embedded
    assert "data:image/png;base64," in html                # png embedded inline
    assert "涡量 vorticity" in html
    assert "abc123" in html and "trusted=True" in html     # audit block
