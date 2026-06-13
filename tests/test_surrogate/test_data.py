"""Smoke + unit tests for surrogate data pipeline (M3-S3).

Tests:
- generate_mock_data produces correct shapes + plausible values
- split_train_val_test is deterministic and sums to n
- Normalizer round-trips correctly
- save/load round-trip preserves data
- Validation catches bad inputs
- CSV loading with header and raw formats
- Dataset merging and statistics
"""

import os
import numpy as np
import pytest

from cfd_harness.surrogate.data import (
    SurrogateDataset,
    Normalizer,
    split_train_val_test,
    save_dataset,
    load_dataset,
    generate_mock_data,
    load_data_from_csv,
    merge_datasets,
    dataset_statistics,
    DEFAULT_INPUT_COLS,
    DEFAULT_TARGET_COLS,
)


class TestGenerateMockData:
    def test_default_generates_100(self):
        ds = generate_mock_data()
        assert ds.n_samples == 100
        assert ds.inputs.shape == (100, 12)
        assert ds.targets.shape == (100, 2)
        ds.validate()

    def test_custom_n(self):
        for n in [10, 50, 200]:
            ds = generate_mock_data(n_samples=n)
            assert ds.n_samples == n

    def test_deterministic_seed(self):
        ds1 = generate_mock_data(n_samples=50, seed=123)
        ds2 = generate_mock_data(n_samples=50, seed=123)
        assert np.allclose(ds1.inputs, ds2.inputs)
        assert np.allclose(ds1.targets, ds2.targets)

    def test_different_seeds_diverge(self):
        ds1 = generate_mock_data(n_samples=50, seed=1)
        ds2 = generate_mock_data(n_samples=50, seed=999)
        assert not np.allclose(ds1.targets, ds2.targets)

    def test_plausible_aero_range(self):
        ds = generate_mock_data(n_samples=200, noise_std=0.01)
        # Cl should be in roughly [0.2, 0.8] range
        assert 0.15 < ds.targets[:, 0].min() < 0.85
        assert 0.15 < ds.targets[:, 0].max() < 0.85
        # Cd should be positive
        assert (ds.targets[:, 1] > 0).all()
        assert ds.targets[:, 1].max() < 0.1

    def test_meta_keys(self):
        ds = generate_mock_data(n_samples=30, seed=7)
        assert "generator" in ds.meta
        assert ds.meta["seed"] == 7


class TestSurrogateDataset:
    def test_validate_ok(self):
        ds = SurrogateDataset(
            inputs=np.random.randn(10, 12),
            targets=np.random.randn(10, 2),
        )
        ds.validate()  # no raise

    def test_validate_bad_input_shape(self):
        ds = SurrogateDataset(
            inputs=np.random.randn(10, 5),
            targets=np.random.randn(10, 2),
        )
        with pytest.raises(ValueError, match="(N, 12)"):
            ds.validate()

    def test_validate_bad_target_shape(self):
        ds = SurrogateDataset(
            inputs=np.random.randn(10, 12),
            targets=np.random.randn(10, 1),
        )
        with pytest.raises(ValueError, match="(N, 2)"):
            ds.validate()

    def test_validate_mismatched_lengths(self):
        ds = SurrogateDataset(
            inputs=np.random.randn(10, 12),
            targets=np.random.randn(5, 2),
        )
        with pytest.raises(ValueError, match="same length"):
            ds.validate()

    def test_validate_nan_inputs(self):
        inputs = np.random.randn(10, 12)
        inputs[3, 0] = np.nan
        ds = SurrogateDataset(inputs=inputs, targets=np.random.randn(10, 2))
        with pytest.raises(ValueError, match="NaN"):
            ds.validate()

    @pytest.mark.parametrize("n", [1, 5, 50])
    def test_properties(self, n):
        ds = SurrogateDataset(
            inputs=np.random.randn(n, 12),
            targets=np.random.randn(n, 2),
        )
        assert ds.n_samples == n
        assert ds.n_features == 12
        assert ds.n_targets == 2


class TestNormalizer:
    def test_fit_transform_roundtrip(self):
        ds = generate_mock_data(n_samples=100)
        norm = Normalizer()
        norm.fit(ds)

        X_norm = norm.transform_inputs(ds.inputs)
        Y_norm = norm.transform_targets(ds.targets)

        # Normalized data should have ~0 mean, ~1 std
        assert np.abs(X_norm.mean()) < 1e-10
        assert np.abs(X_norm.std() - 1.0) < 0.10  # sample std

        # Inverse should recover originals
        Y_back = norm.inverse_transform_targets(Y_norm)
        assert np.allclose(Y_back, ds.targets)

    def test_not_fitted_raises(self):
        norm = Normalizer()
        with pytest.raises(RuntimeError, match="not fitted"):
            _ = norm.input_mean

    def test_zero_std_protection(self):
        # Constant feature column should not cause div-by-zero
        inputs = np.random.randn(50, 12)
        inputs[:, 5] = 3.14  # constant column
        targets = np.random.randn(50, 2)
        ds = SurrogateDataset(inputs=inputs, targets=targets)

        norm = Normalizer()
        norm.fit(ds)
        X_norm = norm.transform_inputs(inputs)
        assert np.isfinite(X_norm).all()
        # The constant column's std was clamped to 1.0
        assert norm.input_std[5] == 1.0

    def test_fit_chainable(self):
        ds = generate_mock_data(n_samples=30)
        norm = Normalizer().fit(ds)
        assert norm.input_mean is not None


class TestSplit:
    def test_sum_to_n(self):
        ds = generate_mock_data(n_samples=100)
        train, val, test = split_train_val_test(ds, train_frac=0.7, val_frac=0.2, seed=42)

        assert train.n_samples + val.n_samples + test.n_samples == 100

    def test_deterministic(self):
        ds = generate_mock_data(n_samples=50)
        t1, v1, te1 = split_train_val_test(ds, seed=42)
        t2, v2, te2 = split_train_val_test(ds, seed=42)
        assert np.allclose(t1.inputs, t2.inputs)
        assert np.allclose(v1.inputs, v2.inputs)
        assert np.allclose(te1.inputs, te2.inputs)

    def test_no_overlap(self):
        ds = generate_mock_data(n_samples=60)
        train, val, test = split_train_val_test(ds, seed=123)

        # Check that no input row appears in two splits
        train_set = set(tuple(row) for row in train.inputs)
        val_set = set(tuple(row) for row in val.inputs)
        test_set = set(tuple(row) for row in test.inputs)
        assert len(train_set & val_set) == 0
        assert len(train_set & test_set) == 0
        assert len(val_set & test_set) == 0

    def test_min_sizes(self):
        ds = generate_mock_data(n_samples=10)
        train, val, test = split_train_val_test(ds, train_frac=0.5, val_frac=0.3)
        assert train.n_samples >= 1
        # val and test may be 0 for tiny n
        assert train.n_samples + (val.n_samples if val else 0) + (test.n_samples if test else 0) == 10


class TestSaveLoad:
    def test_roundtrip(self, tmp_path):
        ds = generate_mock_data(n_samples=50, seed=7)
        path = str(tmp_path / "test_dataset.npz")
        save_dataset(ds, path)

        loaded = load_dataset(path)
        assert np.allclose(loaded.inputs, ds.inputs)
        assert np.allclose(loaded.targets, ds.targets)
        assert loaded.feature_names == ds.feature_names
        assert loaded.target_names == ds.target_names
        assert loaded.meta == ds.meta

    def test_sidecar_meta_written(self, tmp_path):
        ds = generate_mock_data(n_samples=10)
        path = str(tmp_path / "test_meta.npz")
        save_dataset(ds, path)

        meta_path = path.replace(".npz", "_meta.json")
        import json
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["generator"] == "generate_mock_data"
        assert "feature_names" in meta
        assert "target_names" in meta


# ---------------------------------------------------------------------------
# Real data interface tests (B — data enhancement)
# ---------------------------------------------------------------------------

class TestCSVLoading:
    def test_header_csv(self, tmp_path):
        """CSV with named header columns."""
        path = str(tmp_path / "test_data.csv")
        header = ",".join(DEFAULT_INPUT_COLS + DEFAULT_TARGET_COLS)
        # 5 data rows
        rows = []
        rng = np.random.RandomState(42)
        for _ in range(5):
            inputs = rng.uniform(-0.15, 0.15, 12)
            cl = 0.5 + 0.1 * inputs[0]
            cd = 0.03 + 0.01 * abs(inputs[1])
            rows.append(",".join(f"{v:.6f}" for v in list(inputs) + [cl, cd]))
        content = header + "\n" + "\n".join(rows)
        with open(path, "w") as f:
            f.write(content)

        ds = load_data_from_csv(path)
        assert ds.n_samples == 5
        assert ds.inputs.shape == (5, 12)
        assert ds.targets.shape == (5, 2)
        ds.validate()

    def test_header_csv_custom_cols(self, tmp_path):
        """CSV with non-standard column names."""
        path = str(tmp_path / "test_custom.csv")
        custom_inputs = [f"cst_{i}" for i in range(12)]
        custom_targets = ["lift", "drag"]
        header = ",".join(custom_inputs + custom_targets)
        rows = []
        rng = np.random.RandomState(1)
        for _ in range(10):
            vals = rng.uniform(-0.15, 0.15, 12)
            rows.append(",".join(f"{v:.6f}" for v in list(vals) + [0.5, 0.03]))
        content = header + "\n" + "\n".join(rows)
        with open(path, "w") as f:
            f.write(content)

        ds = load_data_from_csv(
            path,
            input_cols=custom_inputs,
            target_cols=custom_targets,
        )
        assert ds.n_samples == 10
        assert np.allclose(ds.targets[:, 0], 0.5)

    def test_no_header_csv(self, tmp_path):
        """CSV without header — raw numeric data."""
        path = str(tmp_path / "test_raw.csv")
        rng = np.random.RandomState(7)
        data = rng.uniform(-0.15, 0.15, (8, 12))
        targets = np.column_stack([0.6 + data[:, 0] * 0.2, 0.03 + np.abs(data[:, 1]) * 0.05])
        full = np.hstack([data, targets])
        np.savetxt(path, full, delimiter=",", fmt="%.6f")

        ds = load_data_from_csv(path)
        assert ds.n_samples == 8
        assert ds.inputs.shape == (8, 12)
        assert ds.targets.shape == (8, 2)
        ds.validate()

    def test_nan_filter(self, tmp_path):
        """Rows with NaN targets should be filtered."""
        path = str(tmp_path / "test_nan.csv")
        header = ",".join(DEFAULT_INPUT_COLS + DEFAULT_TARGET_COLS)
        rows = []
        rng = np.random.RandomState(3)
        for i in range(10):
            vals = rng.uniform(-0.15, 0.15, 12)
            if i == 3:
                cl, cd = "NaN", "inf"
            elif i == 7:
                cl, cd = "0.5", ""  # empty = NaN
            else:
                cl, cd = f"{0.5:.4f}", f"{0.03:.4f}"
            rows.append(",".join(f"{v:.6f}" for v in vals) + f",{cl},{cd}")
        content = header + "\n" + "\n".join(rows)
        with open(path, "w") as f:
            f.write(content)

        ds = load_data_from_csv(path)
        assert ds.n_samples == 8  # 10 - 2 NaN rows
        ds.validate()


class TestMergeDatasets:
    def test_merge_two(self):
        ds1 = generate_mock_data(n_samples=30, seed=1)
        ds2 = generate_mock_data(n_samples=20, seed=2)
        merged = merge_datasets(ds1, ds2)
        assert merged.n_samples == 50
        assert merged.inputs.shape == (50, 12)
        assert merged.targets.shape == (50, 2)
        assert merged.meta["merge_count"] == 2
        assert merged.meta["merge_total_samples"] == 50

    def test_merge_single_is_identity(self):
        ds = generate_mock_data(n_samples=10)
        merged = merge_datasets(ds)
        assert merged.n_samples == ds.n_samples
        assert np.allclose(merged.inputs, ds.inputs)

    def test_merge_three(self):
        ds1 = generate_mock_data(n_samples=10, seed=1)
        ds2 = generate_mock_data(n_samples=10, seed=2)
        ds3 = generate_mock_data(n_samples=10, seed=3)
        merged = merge_datasets(ds1, ds2, ds3)
        assert merged.n_samples == 30


class TestDatasetStatistics:
    def test_all_keys(self):
        ds = generate_mock_data(n_samples=50)
        stats = dataset_statistics(ds)
        assert stats["n_samples"] == 50
        assert stats["n_features"] == 12
        assert stats["n_targets"] == 2
        assert "inputs" in stats
        assert "targets" in stats
        for key in ["mean", "std", "min", "max", "q25", "q50", "q75"]:
            assert key in stats["inputs"]
            assert key in stats["targets"]

    def test_feature_stats_shape(self):
        ds = generate_mock_data(n_samples=30)
        stats = dataset_statistics(ds)
        assert len(stats["inputs"]["mean"]) == 12
        assert len(stats["targets"]["mean"]) == 2
