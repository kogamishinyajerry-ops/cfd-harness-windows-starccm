"""
metrics.py -- Evaluation metrics for surrogate model quality (M3-S4).

All metrics are solver-agnostic, pure numpy, and operate on (N, 2) arrays:
column 0 = Cl, column 1 = Cd.

We evaluate per-output AND multi-output (combined) so the training pipeline
can report both decomposition and aggregate scores.
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Atomic metrics
# ---------------------------------------------------------------------------

def r2(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination R² (per column, averaged).

    R² = 1 - SS_res / SS_tot. Returns float in (-inf, 1.0].
    """
    ss_res = ((y_true - y_pred) ** 2).sum(axis=0)
    ss_tot = ((y_true - y_true.mean(axis=0)) ** 2).sum(axis=0)
    # Protect against constant-target columns
    safe = np.where(ss_tot < 1e-15, 1.0, 1.0 - ss_res / ss_tot)
    return float(safe.mean())


def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error (averaged over columns)."""
    return float(np.abs(y_true - y_pred).mean())


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error (averaged over columns)."""
    return float(np.sqrt(((y_true - y_pred) ** 2).mean()))


def max_error(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Maximum absolute error across all samples and both columns."""
    return float(np.abs(y_true - y_pred).max())


def relative_error(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-8) -> float:
    """Mean relative absolute error (averaged over columns).

    Rel = |y_true - y_pred| / (|y_true| + eps). Clamped to avoid division by tiny numbers.
    """
    rel = np.abs(y_true - y_pred) / (np.abs(y_true) + eps)
    return float(rel.mean())


def coverage_ratio(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_std: np.ndarray,
    k: float = 2.0,
) -> float:
    """Fraction of samples where |y_true - y_pred| <= k * std.

    This is the "uncertainty calibration" metric — for a well-calibrated model
    with normal errors, ~95% of points should fall within 2σ.
    """
    within = np.abs(y_true - y_pred) <= k * y_std
    return float(within.mean())


# ---------------------------------------------------------------------------
# Per-output breakdown
# ---------------------------------------------------------------------------

def evaluate_per_output(
    y_true: np.ndarray, y_pred: np.ndarray, output_names: Optional[List[str]] = None
) -> Dict[str, Dict[str, float]]:
    """Compute R², MAE, RMSE separately for each output column.

    Returns:
        {"Cl": {"r2": ..., "mae": ..., "rmse": ...}, "Cd": {...}}
    """
    if output_names is None:
        output_names = ["Cl", "Cd"]
    result = {}
    for i, name in enumerate(output_names):
        yt = y_true[:, i : i + 1]
        yp = y_pred[:, i : i + 1]
        result[name] = {
            "r2": r2(yt, yp),
            "mae": mae(yt, yp),
            "rmse": rmse(yt, yp),
            "max_error": max_error(yt, yp),
        }
    return result


# ---------------------------------------------------------------------------
# Combined evaluation
# ---------------------------------------------------------------------------

def evaluate_all(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    y_std: Optional[np.ndarray] = None,
    label: str = "test",
) -> Dict[str, float]:
    """Single-call evaluation returning all metrics as a flat dict.

    Keys:
        r2, mae, rmse, max_error, relative_error,
        (optional) coverage_2sigma  — if y_std is provided
    """
    result: Dict[str, float] = {
        f"{label}_r2": r2(y_true, y_pred),
        f"{label}_mae": mae(y_true, y_pred),
        f"{label}_rmse": rmse(y_true, y_pred),
        f"{label}_max_error": max_error(y_true, y_pred),
        f"{label}_relative_error": relative_error(y_true, y_pred),
    }
    if y_std is not None:
        result[f"{label}_coverage_2sigma"] = coverage_ratio(
            y_true, y_pred, y_std, k=2.0
        )
    return result


# ---------------------------------------------------------------------------
# Multi-output parity check helper
# ---------------------------------------------------------------------------

def parity_summary(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_names: Optional[List[str]] = None,
) -> Dict[str, Dict[str, float]]:
    """Full parity report: combined + per-output.

    Returns:
        {
            "combined": {r2, mae, rmse, max_error, relative_error},
            "per_output": {"Cl": {...}, "Cd": {...}}
        }
    """
    if output_names is None:
        output_names = ["Cl", "Cd"]
    return {
        "combined": evaluate_all(y_true, y_pred),
        "per_output": evaluate_per_output(y_true, y_pred, output_names),
    }


__all__ = [
    "r2",
    "mae",
    "rmse",
    "max_error",
    "relative_error",
    "coverage_ratio",
    "evaluate_per_output",
    "evaluate_all",
    "parity_summary",
]
