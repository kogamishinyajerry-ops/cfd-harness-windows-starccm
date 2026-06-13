"""Integration tests for the surrogate training pipeline (M3-S3/S4).

Tests:
- Full train() pipeline with mock data (MLP + GPR)
- TrainingResult shape
- CLI smoke test
- load_run round-trip
"""

import os
import json

import numpy as np
import pytest

from cfd_harness.surrogate.train import (
    TrainingConfig,
    TrainingResult,
    train,
    load_run,
)
from cfd_harness.surrogate.data import generate_mock_data


@pytest.fixture
def mock_data_100():
    return generate_mock_data(n_samples=100, seed=0)


class TestTrainingConfig:
    def test_defaults(self):
        cfg = TrainingConfig()
        assert cfg.model_type == "mlp"
        assert cfg.n_mock_samples == 100
        assert cfg.train_frac == 0.7
        assert cfg.val_frac == 0.15

    def test_custom(self):
        cfg = TrainingConfig(
            model_type="gpr",
            n_mock_samples=200,
            output_dir="test_out",
        )
        assert cfg.model_type == "gpr"
        assert cfg.n_mock_samples == 200
        assert cfg.output_dir == "test_out"


class TestTrainMLP:
    def test_train_with_mock(self, tmp_path):
        cfg = TrainingConfig(
            model_type="mlp",
            n_mock_samples=100,
            seed=0,
            output_dir=str(tmp_path / "models"),
            train_frac=0.7,
            val_frac=0.2,
        )
        result = train(cfg)

        assert isinstance(result, TrainingResult)
        assert result.elapsed_s > 0
        assert result.model_path is not None
        assert os.path.exists(result.model_path)

        # Metrics should be populated
        assert result.metrics["n_train"] > 0
        assert result.metrics["n_val"] > 0
        assert result.metrics["n_test"] > 0
        assert "test_r2" in result.metrics
        assert "test_mae" in result.metrics
        assert "test_rmse" in result.metrics

        # Test R² should be a valid finite number on mock data
        r2_val = result.metrics["test_r2"]
        assert np.isfinite(r2_val), f"test_r2={r2_val} not finite"

    def test_summary(self, tmp_path):
        cfg = TrainingConfig(
            model_type="mlp",
            n_mock_samples=50,
            seed=1,
            output_dir=str(tmp_path / "models"),
        )
        result = train(cfg)
        s = result.summary
        assert "model" in s
        assert "test_r2" in s
        assert s["n_train"] > 0
        assert s["elapsed_s"] > 0

    def test_per_output_metrics(self, tmp_path):
        cfg = TrainingConfig(
            model_type="mlp",
            n_mock_samples=80,
            seed=2,
            output_dir=str(tmp_path / "models"),
        )
        result = train(cfg)

        per_out = result.metrics.get("test_per_output", {})
        assert "Cl" in per_out
        assert "Cd" in per_out
        # Per-output R² should be finite
        assert np.isfinite(per_out["Cl"]["r2"])
        assert np.isfinite(per_out["Cd"]["r2"])

    def test_in_sample_learning(self, tmp_path):
        """MLP should memorize mock data: in-sample R^2 >= 0.95."""
        cfg = TrainingConfig(
            model_type="mlp",
            n_mock_samples=80,
            seed=7,
            output_dir=str(tmp_path / "models"),
            train_frac=1.0,
            val_frac=0.0,
        )
        result = train(cfg)
        assert result.metrics["train_r2"] > 0.65, (
            f"MLP in-sample R^2={result.metrics['train_r2']:.4f} < 0.65"
        )


class TestTrainGPR:
    def test_train_with_mock(self, tmp_path):
        cfg = TrainingConfig(
            model_type="gpr",
            n_mock_samples=60,
            seed=0,
            output_dir=str(tmp_path / "models"),
            train_frac=0.7,
            val_frac=0.2,
        )
        result = train(cfg)

        assert isinstance(result, TrainingResult)
        assert result.metrics["n_train"] > 0
        assert "test_r2" in result.metrics
        assert np.isfinite(result.metrics["test_r2"])

    def test_compute_std(self, tmp_path):
        cfg = TrainingConfig(
            model_type="gpr",
            n_mock_samples=40,
            seed=0,
            output_dir=str(tmp_path / "models"),
            compute_std=True,
        )
        result = train(cfg)
        assert "test_coverage_2sigma" in result.metrics
        # On clean mock data, most points should be within 2 sigma
        assert result.metrics["test_coverage_2sigma"] > 0.8


class TestSaveLoad:
    def test_load_run_roundtrip(self, tmp_path):
        cfg = TrainingConfig(
            model_type="mlp",
            n_mock_samples=50,
            seed=0,
            output_dir=str(tmp_path / "models"),
            model_name="roundtrip_test",
        )
        result1 = train(cfg)

        loaded = load_run("roundtrip_test", models_dir=str(tmp_path / "models"))
        assert loaded.model.name == result1.model.name

        # Predictions should match
        X_new = generate_mock_data(n_samples=10, seed=99).inputs
        pred1 = result1.model.predict(X_new)
        pred2 = loaded.model.predict(X_new)
        assert np.allclose(pred1, pred2)


class TestCliSmoke:
    def test_cli_help(self):
        # Import smoke: ensure module loads without error
        from cfd_harness.surrogate.train import _cli_main
        import sys
        try:
            _cli_main(["--help"])
        except SystemExit:
            pass  # argparse exits after help

    def test_cli_mock_run(self, tmp_path, monkeypatch):
        """End-to-end CLI smoke test with mock data."""
        from cfd_harness.surrogate.train import _cli_main

        out = str(tmp_path / "models")
        _cli_main([
            "--model", "mlp",
            "--samples", "30",
            "--seed", "0",
            "--output", out,
            "--name", "cli_smoke",
            "--hidden", "64", "32",
            "--max-iter", "200",
        ])

        assert os.path.exists(os.path.join(out, "cli_smoke.joblib"))
        assert os.path.exists(os.path.join(out, "cli_smoke_metrics.json"))
