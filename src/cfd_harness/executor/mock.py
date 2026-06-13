"""MockExecutor · ExecutorMode.MOCK.

Synthetic executor that bypasses any real solver. Used for tests and
the chief engineer's mock-first smoke loop. Per EXECUTOR_ABSTRACTION
§6.1, MOCK's TrustGate verdict ceiling is `WARN` (never `PASS`),
with note `mock_executor_no_truth_source`.

Plane: EXECUTION (same as `base.py`).
"""
from __future__ import annotations

from typing import ClassVar, Dict

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from cfd_harness.models import ExecutionResult, FlowType, TaskSpec

__all__ = ["MockExecutor"]


# Per-flow-type synthetic presets. Values are deliberately non-physical —
# they signal "synthetic" in any audit report that compares them against
# gold standards (combined with `is_mock=True` and the
# `mock_executor_no_truth_source` note).
_PRESETS: Dict[str, Dict[str, object]] = {
    "internal": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "u_centerline": [0.0, -0.037, 0.025, 0.333, 1.0],
            "mock_preset_marker": True,
        },
    },
    "external": {
        "residuals": {"p": 1e-5, "U": 1e-5},
        "key_quantities": {
            "strouhal_number": 0.165,
            "cd_mean": 1.36,
            "cl_rms": 0.048,
            "mock_preset_marker": True,
        },
    },
    "natural_convection": {
        "residuals": {"p": 1e-6, "T": 1e-7},
        "key_quantities": {
            "nusselt_number": 4.52,
            "mock_preset_marker": True,
        },
    },
}


# Per-case-id synthetic presets (added 2026-06-11, v0.1.1).
# These take precedence over _PRESETS when a case_id is matched —
# this lets the harness ship 16 cases out of the box with mock
# data that overlaps each case's gold_standard quantity list, so
# the comparator has something to compare against (the worst-case
# relative error still drives a WARN verdict, never a false PASS,
# because MOCK is capped at WARN per EXECUTOR_ABSTRACTION §6.1).
#
# The values here are SYNTHETIC — they look physically reasonable
# but are NOT from a real solver run. Combined with
# `is_mock=True` and the `mock_executor_no_truth_source` note,
# any audit consumer should treat them as "smoke", not "truth".
_CASE_PRESETS: Dict[str, Dict[str, object]] = {
    # INTERNAL group
    "lid_driven_cavity": _PRESETS["internal"],   # explicit alias for the 3 anchor
    "backward_facing_step": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "reattachment_length_ratio": 6.05,   # 0.8% off gold=6.10 (within 5%)
            "mock_preset_marker": True,
        },
    },
    "backward_facing_step_steady": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "reattachment_length_ratio_Re100": 2.95,   # 1.7% off gold=3.0
            "reattachment_length_ratio_Re200": 4.45,   # 1.1% off gold=4.5
            "reattachment_length_ratio_Re600": 6.05,   # 0.8% off gold=6.10
            "mock_preset_marker": True,
        },
    },
    "duct_flow": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "poiseuille_number": 63.5,           # 0.8% off gold=64
            "fanning_friction_factor": 0.0438,   # 2.6% off gold=0.0427
            "mock_preset_marker": True,
        },
    },
    "fully_developed_plane_channel_flow": {
        "residuals": {"p": 1e-6, "U": 1e-6},
        "key_quantities": {
            "u_max_to_ubulk_ratio": 1.49,        # 0.7% off gold=1.5
            "wall_shear_stress": 6.05,            # 0.8% off gold=6.0
            "mock_preset_marker": True,
        },
    },
    "plane_channel_flow": {
        "residuals": {"p": 1e-6, "U": 1e-6, "k": 1e-6},
        "key_quantities": {
            "reynolds_stress_uu_plus": 1.02,     # 2% off gold=1.0 (within 10%)
            "mean_velocity_u_plus": [8.4, 14.2, 23.5, 37.5],  # ~1-2% off gold samples
            "mock_preset_marker": True,
        },
    },
    # EXTERNAL group
    "naca0012_airfoil": _PRESETS["external"],   # explicit alias for the 3 anchor
    "circular_cylinder_wake": _PRESETS["external"],   # explicit alias for the 3 anchor
    "axisymmetric_impinging_jet": {
        "residuals": {"p": 1e-5, "U": 1e-5, "T": 1e-7},
        "key_quantities": {
            "stagnation_nusselt": 39.8,          # 3.4% off gold=41.2 (within 10%)
            "nusselt_radial_profile": [40.0, 33.5, 20.1, 7.5, 2.9],  # within 15%
            "mock_preset_marker": True,
        },
    },
    "cylinder_crossflow": {
        "residuals": {"p": 1e-5, "U": 1e-5},
        "key_quantities": {
            "strouhal_number": 0.220,            # 2.3% off gold=0.215
            "cd_mean": 0.95,                     # 3% off gold=0.98
            "mock_preset_marker": True,
        },
    },
    "impinging_jet": {
        "residuals": {"p": 1e-5, "U": 1e-5, "T": 1e-7},
        "key_quantities": {
            "stagnation_nusselt": 34.2,          # 3.9% off gold=35.6
            "nusselt_radial_profile": [34.5, 27.2, 16.2, 6.1],  # within 15%
            "mock_preset_marker": True,
        },
    },
    "turbulent_flat_plate": {
        "residuals": {"p": 1e-5, "U": 1e-5},
        "key_quantities": {
            "skin_friction_cf": 0.00462,         # 1.7% off gold=0.0047
            "displacement_thickness_reynolds": 3350.0,  # 2.9% off gold=3450
            "mock_preset_marker": True,
        },
    },
    # NATURAL_CONVECTION group
    "differential_heated_cavity": {
        "residuals": {"p": 1e-6, "U": 1e-6, "T": 1e-7},
        "key_quantities": {
            "nusselt_hot_wall_Ra1e3": 1.110,     # 0.7% off gold=1.118
            "nusselt_hot_wall_Ra1e5": 4.45,      # 1.5% off gold=4.519
            "mock_preset_marker": True,
        },
    },
    "rayleigh_benard_convection": {
        "residuals": {"p": 1e-6, "T": 1e-7},
        "key_quantities": {
            "nusselt_scaling_exponent": 0.30,    # 3.2% off gold=0.31
            "nusselt_at_Ra1e6": 8.5,             # 2.3% off gold=8.7
            "mock_preset_marker": True,
        },
    },
    # CONJUGATE group
    "cht_pipe_gnielinski": {
        "residuals": {"p": 1e-5, "U": 1e-5, "T": 1e-7},
        "key_quantities": {
            "nusselt_Re10000_Pr07": 62.7,        # 2.5% off gold=64.3
            "nusselt_Re100000_Pr07": 374.0,      # 3.1% off gold=386.0
            "mock_preset_marker": True,
        },
    },
    "cht_straight_fin": {
        "residuals": {"p": 1e-5, "U": 1e-5, "T": 1e-7},
        "key_quantities": {
            "fin_efficiency": 0.948,             # 0.9% off gold=0.957
            "fin_temperature_drop": 0.0415,      # 3.5% off gold=0.043
            "mock_preset_marker": True,
        },
    },
}


def _flow_key(task_spec: TaskSpec) -> str:
    flow = task_spec.flow_type
    if isinstance(flow, FlowType):
        return flow.value
    return str(flow).lower()


class MockExecutor(ExecutorAbc):
    """ExecutorMode.MOCK — TrustGate verdict ceiling = WARN (never PASS).

    The `mock_executor_no_truth_source` note is attached to every
    RunReport this class produces, so downstream TrustGate routing per
    EXECUTOR_ABSTRACTION §6.1 can apply the WARN ceiling without
    special-casing.
    """
    MODE: ClassVar[ExecutorMode] = ExecutorMode.MOCK

    _CEILING_NOTE: ClassVar[str] = "mock_executor_no_truth_source"

    def execute(self, task_spec: TaskSpec) -> RunReport:
        # _CASE_PRESETS (by case_id) takes precedence over _PRESETS
        # (by flow_type). Falls back to the flow_type preset for
        # unknown case_ids, then to the "internal" preset.
        preset = _CASE_PRESETS.get(task_spec.case_id)
        if preset is None:
            preset = _PRESETS.get(_flow_key(task_spec), _PRESETS["internal"])
        execution = ExecutionResult(
            success=True,
            is_mock=True,
            residuals=dict(preset["residuals"]),  # type: ignore[arg-type]
            key_quantities=dict(preset["key_quantities"]),  # type: ignore[arg-type]
            execution_time_s=0.01,
            raw_output_path=None,
        )
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=execution,
            notes=(self._CEILING_NOTE,),
        )
