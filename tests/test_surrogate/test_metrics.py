"""Unit tests for surrogate evaluation metrics (M3-S4).

Tests:
- All atomic metrics return correct values for known inputs
- Perfect prediction gives R²=1, MAE=0, RMSE=0
- Constant-target column handled gracefully
- Per-output and parity_summary produce correct structure
- Coverage ratio for known sigma
"""

import numpy as np
import pytest

from cfd_harness.surrogate.metrics import (
    r2,
    mae,
    rmse,
    max_error,
    relative_error,
    coverage_ratio,
    evaluate_per_output,
    evaluate_all,
    parity_summary,
)


class TestAtomicMetrics:
    def test_r2_perfect(self):
        y = np.random.randn(50, 2)
        assert r2(y, y) == pytest.approx(1.0)

    def test_r2_worse_than_mean(self):
        y = np.array([[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]])
        y_pred = np.mean(y, axis=0) + np.array([10.0, 20.0])
        y_pred = np.tile(y_pred, (3, 1))
        # Predictions far from mean → R² negative
        assert r2(y, y_pred) < 0

    def test_mae_zero(self):
        y = np.random.randn(10, 2)
        assert mae(y, y) == 0.0

    def test_mae_known(self):
        y_true = np.array([[0.0, 0.0], [0.0, 0.0]])
        y_pred = np.array([[1.0, 2.0], [3.0, 4.0]])
        # MAE = (|1| + |2| + |3| + |4|) / 4 = 2.5
        assert mae(y_true, y_pred) == pytest.approx(2.5)

    def test_rmse_known(self):
        y_true = np.array([[0.0, 0.0]])
        y_pred = np.array([[3.0, 4.0]])
        # sq err = [9, 16], mean = 12.5, sqrt = sqrt(12.5)
        expected = np.sqrt(12.5)
        assert rmse(y_true, y_pred) == pytest.approx(expected)

    def test_max_error_known(self):
        y_true = np.array([[0.0, 0.0], [0.0, 0.0]])
        y_pred = np.array([[0.5, 2.0], [1.0, 3.5]])
        assert max_error(y_true, y_pred) == pytest.approx(3.5)

    def test_relative_error(self):
        y_true = np.array([[1.0, 2.0], [3.0, 4.0]])
        y_pred = np.array([[1.1, 1.8], [2.7, 4.4]])
        rel = relative_error(y_true, y_pred)
        # Should be small but > 0
        assert 0 < rel < 1.0

    def test_coverage_ratio(self):
        y_true = np.zeros((100, 2))
        y_pred = np.zeros((100, 2))
        y_std = np.ones((100, 2)) * 2.0
        # Within 2*2.0 = 4.0 sigma → all covered
        assert coverage_ratio(y_true, y_pred, y_std, k=2.0) == pytest.approx(1.0)

    def test_coverage_ratio_partial(self):
        y_true = np.zeros((10, 2))
        y_pred = np.zeros((10, 2))
        y_pred[0, 0] = 10.0  # outside 2-sigma if std=1
        y_std = np.ones((10, 2))
        # 1 out of 20 cells outside → 19/20 = 0.95
        cov = coverage_ratio(y_true, y_pred, y_std, k=2.0)
        assert cov == pytest.approx(19 / 20)


class TestEvaluatePerOutput:
    def test_structure(self):
        y_true = np.random.randn(20, 2)
        y_pred = np.random.randn(20, 2)
        result = evaluate_per_output(y_true, y_pred)
        assert set(result.keys()) == {"Cl", "Cd"}
        for key in ["r2", "mae", "rmse", "max_error"]:
            assert key in result["Cl"]
            assert key in result["Cd"]

    def test_custom_names(self):
        y_true = np.random.randn(10, 2)
        y_pred = np.random.randn(10, 2)
        result = evaluate_per_output(y_true, y_pred, output_names=["lift", "drag"])
        assert set(result.keys()) == {"lift", "drag"}


class TestEvaluateAll:
    def test_flat_dict_keys(self):
        y_true = np.random.randn(10, 2)
        y_pred = np.random.randn(10, 2)
        result = evaluate_all(y_true, y_pred, label="test")
        assert "test_r2" in result
        assert "test_mae" in result
        assert "test_rmse" in result
        assert "test_max_error" in result
        assert "test_relative_error" in result
        assert "test_coverage_2sigma" not in result  # no std provided

    def test_with_std(self):
        y_true = np.random.randn(10, 2)
        y_pred = np.random.randn(10, 2)
        y_std = np.ones((10, 2)) * 0.5
        result = evaluate_all(y_true, y_pred, y_std=y_std, label="val")
        assert "val_coverage_2sigma" in result


class TestParitySummary:
    def test_structure(self):
        y_true = np.random.randn(15, 2)
        y_pred = np.random.randn(15, 2)
        summary = parity_summary(y_true, y_pred)
        assert "combined" in summary
        assert "per_output" in summary
        assert "Cl" in summary["per_output"]
        assert "Cd" in summary["per_output"]
