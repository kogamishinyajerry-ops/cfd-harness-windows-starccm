"""Tests for case profile validation."""

import pytest

from cfd_harness.starccm_adapter.case_profiles import (
    validate_profiles,
    get_case_list,
    get_cases_by_status,
    count_cases,
)


class TestCaseProfiles:
    def test_all_profiles_valid(self):
        """Every case in case_profiles.yaml must validate clean."""
        errors = validate_profiles()
        assert errors == {}, (
            f"Case profile validation errors:\n"
            + "\n".join(f"  {k}: {v}" for k, v in errors.items())
        )

    def test_count_at_least_16(self):
        """We expect 16 main cases (3 anchor + 13 mock_only)."""
        cases = get_case_list()
        assert len(cases) >= 16, f"Expected >=16 cases, got {len(cases)}"

    def test_wired_cases_exist(self):
        """3 anchor cases should be 'wired'."""
        wired = get_cases_by_status("wired")
        assert len(wired) == 3, f"Expected 3 wired, got {len(wired)}: {wired}"
        assert "lid_driven_cavity" in wired
        assert "naca0012_airfoil" in wired
        assert "circular_cylinder_wake" in wired

    def test_mock_only_cases(self):
        """13 mock_only cases for the remaining gold standards."""
        mock = get_cases_by_status("mock_only")
        # 13 + 4 rotor family = 17 mock_only
        assert len(mock) >= 13, f"Expected >=13 mock_only, got {len(mock)}: {mock}"

    def test_count_by_status(self):
        counts = count_cases()
        assert counts.get("wired", 0) == 3
        assert counts.get("mock_only", 0) >= 13

    def test_specific_mock_cases_exist(self):
        """Key mock cases should be present."""
        cases = set(get_case_list())
        expected = {
            "backward_facing_step",
            "duct_flow",
            "fully_developed_plane_channel_flow",
            "plane_channel_flow",
            "turbulent_flat_plate",
            "impinging_jet",
            "differential_heated_cavity",
            "rayleigh_benard_convection",
            "cht_pipe_gnielinski",
            "cht_straight_fin",
            "cylinder_crossflow",
            "axisymmetric_impinging_jet",
            "backward_facing_step_steady",
        }
        missing = expected - cases
        assert not missing, f"Missing cases: {missing}"
