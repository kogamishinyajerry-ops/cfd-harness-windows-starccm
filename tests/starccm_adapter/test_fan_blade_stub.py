"""Smoke test for cfd_harness.starccm_adapter.case_solve.fan_blade stub.

This is a 7 月期 stub-level smoke test. It does NOT run STAR-CCM+; it
only verifies the surface shape of ``build_case`` and ``extract_aero``:

  - ``build_case`` returns a ``pathlib.Path`` and writes the marker
    macro file into ``output_dir``;
  - ``extract_aero`` returns a ``dict`` with the 4 expected keys
    (cl, cd, PR, eta_is), all ``None`` when no _summary.json exists.

Real-solver tests land in 8 月数据期 ① alongside the
Rotor37Slice.java macro.

References:
  - verdict-2026-07 §5.2 D-4 (this stub is the deliverable)
  - track-d-deliverable.md §3 ★ 3 (the ROI entry)
  - CHARTER.md §2 数据期 ① (8 月 plan that consumes this entry)
"""
from __future__ import annotations

from pathlib import Path

from cfd_harness.starccm_adapter.case_solve import fan_blade


def test_build_case_returns_path_and_writes_marker_macro(tmp_path: Path) -> None:
    """build_case returns a Path and drops a marker .java into output_dir.

    The marker .java is the only file the stub writes; the .sim is
    intentionally NOT created (the stub does not spawn STAR-CCM+).
    """
    output_dir = tmp_path / "rotor37_out"
    sim_path = fan_blade.build_case(
        rotor_yaml="knowledge/gold_standards/rotor37.yaml",  # does not exist yet
        output_dir=str(output_dir),
    )

    # Shape contract: Path, ending with .sim
    assert isinstance(sim_path, Path)
    assert sim_path.suffix == ".sim"
    assert "PLACEHOLDER" in sim_path.name  # stub signals "not a real .sim"

    # Marker macro was written
    marker = output_dir / "stub_rotor_macro.java"
    assert marker.exists()
    assert "STUB" in marker.read_text(encoding="utf-8")


def test_build_case_tolerates_missing_rotor_yaml(tmp_path: Path) -> None:
    """build_case does not crash if the gold-standard yaml is absent.

    The 7 月期 track-c 草稿 has __TO_FILL_FROM_LIT__ placeholders and
    the real rotor37.yaml is itself HIGH-severity debt (D-2). The
    stub must remain callable before the gold standard lands.
    """
    output_dir = tmp_path / "rotor37_no_yaml"
    sim_path = fan_blade.build_case(
        rotor_yaml="knowledge/gold_standards/this_does_not_exist.yaml",
        output_dir=str(output_dir),
    )
    assert isinstance(sim_path, Path)
    assert (output_dir / "stub_rotor_macro.java").exists()


def test_extract_aero_returns_dict_shape_with_none_values(tmp_path: Path) -> None:
    """extract_aero returns the 4-key shape, all None when no summary."""
    fake_sim = tmp_path / "rotor37_slice_solved.sim"
    fake_sim.touch()  # file exists, but no _summary.json sibling
    result = fan_blade.extract_aero(str(fake_sim))

    assert isinstance(result, dict)
    assert set(result.keys()) == {"cl", "cd", "PR", "eta_is"}
    assert all(v is None for v in result.values())


def test_aero_keys_constant_matches_docstring() -> None:
    """The 4 quantity names are part of the up-stack contract.

    Track A §1.3 + verdict §5.2 C1 list total_temperature_ratio as a
    FlowType.ROTOR_COMPRESSOR quantity that the 7 月 V&V engine does NOT
    yet track; we keep the 7 月 stub at the 4 mechanical-engineering
    staples (cl, cd, PR, eta_is) and add total_temperature_ratio in
    8 月 alongside D-9's FlowType.ROTOR_COMPRESSOR enum extension.
    """
    assert fan_blade._AERO_KEYS == ("cl", "cd", "PR", "eta_is")
