"""Tests for the auto-verifier's gold_standard_comparator — the V&V core."""
from __future__ import annotations

from pathlib import Path

import pytest

from cfd_harness.auto_verifier.gold_standard_comparator import GoldStandardComparator


def test_missing_gold_returns_failing(tmp_path: Path):
    cmp = GoldStandardComparator()
    r = cmp.compare(tmp_path / "nonexistent.yaml", {"u_centerline": [0.0]})
    assert not r.all_pass
    assert "__gold_anchor_missing__" in r.failing_quantities


def test_lid_driven_cavity_u_centerline_passes_within_tolerance(ldc_task_spec, gold_root):
    """The LDC u_centerline reference values are within 5% of themselves."""
    cmp = GoldStandardComparator(tolerance_floor=0.05)
    # Use the Ghia values themselves as the measured values.
    measured = [0.0, -0.042, -0.077, -0.109, -0.141, -0.166, -0.186, -0.206,
                -0.206, -0.169, -0.127, -0.053, 0.034, 0.155, 0.337, 0.617, 1.0]
    r = cmp.compare(gold_root / "lid_driven_cavity.yaml", {"u_centerline": measured})
    # Allow WARN due to 1% rounding; must not be FAIL.
    failing = [q for q in r.quantities if not q.all_pass]
    assert len(failing) == 0, f"u_centerline should pass within 5%; got {failing}"


def test_lid_driven_cavity_u_centerline_fails_above_tolerance(ldc_task_spec, gold_root):
    """A 10% perturbation exceeds the 5% tolerance and MUST fail."""
    cmp = GoldStandardComparator(tolerance_floor=0.05)
    # Same values but +10% — should fail.
    measured = [v * 1.10 for v in [0.0, -0.042, -0.077, -0.109, -0.141, -0.166,
                                    -0.186, -0.206, -0.206, -0.169, -0.127, -0.053,
                                    0.034, 0.155, 0.337, 0.617, 1.0]]
    r = cmp.compare(gold_root / "lid_driven_cavity.yaml", {"u_centerline": measured})
    assert not r.all_pass
    assert "u_centerline" in r.failing_quantities


def test_lid_driven_cavity_2pct_within_tolerance(ldc_task_spec, gold_root):
    """A 2% perturbation is within the 5% tolerance and MUST pass."""
    cmp = GoldStandardComparator(tolerance_floor=0.05)
    measured = [v * 1.02 for v in [0.0, -0.042, -0.077, -0.109, -0.141, -0.166,
                                    -0.186, -0.206, -0.206, -0.169, -0.127, -0.053,
                                    0.034, 0.155, 0.337, 0.617, 1.0]]
    r = cmp.compare(gold_root / "lid_driven_cavity.yaml", {"u_centerline": measured})
    # u_centerline should pass; v_centerline and primary_vortex_location
    # are missing from the measured dict — they should be flagged as
    # missing and the overall verdict is FAIL with warnings.
    assert r.failing_quantities  # at least the missing ones
    u_result = next((q for q in r.quantities if q.name == "u_centerline"), None)
    assert u_result is not None
    assert u_result.all_pass is True, "u_centerline at 2% must pass within 5% tolerance"


def test_naca_cl_within_tolerance(naca_task_spec, gold_root):
    """NACA cl=0.235 at ±1% within 2% tolerance → passes."""
    cmp = GoldStandardComparator(tolerance_floor=0.05)
    r = cmp.compare(gold_root / "naca0012_airfoil.yaml", {"cl_alpha2": 0.235 * 1.01})
    cl_result = next((q for q in r.quantities if q.name == "cl_alpha2"), None)
    assert cl_result is not None
    assert cl_result.all_pass is True


def test_cylinder_strouhal_within_tolerance(cylinder_task_spec, gold_root):
    """Williamson Re=200 St=0.198 ±5% within 3% tolerance — need 1% perturbation."""
    cmp = GoldStandardComparator(tolerance_floor=0.05)
    r = cmp.compare(gold_root / "circular_cylinder_wake.yaml", {"strouhal_number": 0.198 * 1.01})
    st_result = next((q for q in r.quantities if q.name == "strouhal_number"), None)
    assert st_result is not None
    # 1% perturbation is within 3% tolerance for this case (configured via thresholds).
    assert st_result.all_pass is True


def test_comparator_tolerance_floor_validation():
    with pytest.raises(ValueError, match="tolerance_floor must be > 0"):
        GoldStandardComparator(tolerance_floor=0.0)
    with pytest.raises(ValueError, match="tolerance_floor must be > 0"):
        GoldStandardComparator(tolerance_floor=-0.01)
