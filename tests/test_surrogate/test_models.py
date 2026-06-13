"""Smoke + unit tests for surrogate model implementations (M3-S3).

Tests:
- MLPSurrogate and GPRSurrogate train and predict on small mock data
- shape correctness of inputs/outputs
- Deterministic with seeded random_state
- predict_single convenience works
- Ensemble averages correctly
- create_model factory
"""

import numpy as np
import pytest

from cfd_harness.surrogate.models import (
    MLPSurrogate,
    GPRSurrogate,
    EnsembleSurrogate,
    create_model,
    _MODEL_REGISTRY,
)
from cfd_harness.surrogate.data import generate_mock_data


@pytest.fixture(scope="module")
def small_dataset():
    return generate_mock_data(n_samples=60, seed=0)


@pytest.fixture
def X_train(small_dataset):
    return small_dataset.inputs[:40]


@pytest.fixture
def Y_train(small_dataset):
    return small_dataset.targets[:40]


@pytest.fixture
def X_test(small_dataset):
    return small_dataset.inputs[40:]


@pytest.fixture
def Y_test(small_dataset):
    return small_dataset.targets[40:]


class TestMLPSurrogate:
    def test_fit_predict_shape(self, X_train, Y_train, X_test):
        model = MLPSurrogate(random_state=42)
        model.fit(X_train, Y_train)
        pred = model.predict(X_test)

        assert pred.shape == (20, 2)
        assert np.isfinite(pred).all()

    def test_deterministic(self, X_train, Y_train, X_test):
        m1 = MLPSurrogate(random_state=42).fit(X_train, Y_train)
        m2 = MLPSurrogate(random_state=42).fit(X_train, Y_train)
        assert np.allclose(m1.predict(X_test), m2.predict(X_test))

    def test_not_fitted_raises(self, X_test):
        model = MLPSurrogate()
        with pytest.raises(RuntimeError, match="not fitted"):
            model.predict(X_test)

    def test_predict_single(self, X_train, Y_train):
        model = MLPSurrogate(random_state=42).fit(X_train, Y_train)
        single = X_train[0]  # (12,)
        pred = model.predict_single(single)
        assert pred.shape == (2,)

    def test_predict_single_bad_shape(self, X_train, Y_train):
        model = MLPSurrogate(random_state=42).fit(X_train, Y_train)
        with pytest.raises(AssertionError):
            model.predict_single(np.array([1.0, 2.0]))  # (2,) not (12,)

    def test_metadata(self, X_train, Y_train):
        model = MLPSurrogate(random_state=42).fit(X_train, Y_train)
        meta = model.get_metadata()
        assert "n_iter" in meta
        assert "loss" in meta
        assert meta["n_iter"] > 0

    def test_get_params(self):
        model = MLPSurrogate(hidden_layer_sizes=(128, 64), max_iter=500)
        params = model.get_params()
        assert params["hidden_layer_sizes"] == [128, 64]
        assert params["max_iter"] == 500

    def test_name(self):
        model = MLPSurrogate(hidden_layer_sizes=(256, 128, 64))
        assert "MLP" in model.name
        assert "256" in model.name


class TestGPRSurrogate:
    def test_fit_predict_shape(self, X_train, Y_train, X_test):
        model = GPRSurrogate(random_state=42)
        model.fit(X_train, Y_train)
        pred = model.predict(X_test)

        assert pred.shape == (20, 2)
        assert np.isfinite(pred).all()

    def test_deterministic(self, X_train, Y_train, X_test):
        m1 = GPRSurrogate(random_state=42).fit(X_train, Y_train)
        m2 = GPRSurrogate(random_state=42).fit(X_train, Y_train)
        assert np.allclose(m1.predict(X_test), m2.predict(X_test))

    def test_predict_with_std(self, X_train, Y_train, X_test):
        model = GPRSurrogate(random_state=42).fit(X_train, Y_train)
        mean, std = model.predict_with_std(X_test)
        assert mean.shape == (20, 2)
        assert std.shape == (20, 2)  # multi-output GPR returns per-output std
        assert (std > 0).all()

    def test_metadata(self, X_train, Y_train):
        model = GPRSurrogate(random_state=42).fit(X_train, Y_train)
        meta = model.get_metadata()
        assert "kernel" in meta
        assert "log_marginal_likelihood" in meta

    def test_name(self):
        model = GPRSurrogate()
        assert "GPR" in model.name


class TestEnsembleSurrogate:
    def test_averages_correctly(self, X_train, Y_train, X_test):
        mlp = MLPSurrogate(random_state=1)
        gpr = GPRSurrogate(random_state=1)
        ens = EnsembleSurrogate([mlp, gpr])

        ens.fit(X_train, Y_train)
        pred_ens = ens.predict(X_test)

        mlp2 = MLPSurrogate(random_state=1).fit(X_train, Y_train)
        gpr2 = GPRSurrogate(random_state=1).fit(X_train, Y_train)

        pred_avg = (mlp2.predict(X_test) + gpr2.predict(X_test)) / 2.0
        assert np.allclose(pred_ens, pred_avg)

    def test_name(self):
        mlp = MLPSurrogate(hidden_layer_sizes=(64,))
        gpr = GPRSurrogate()
        ens = EnsembleSurrogate([mlp, gpr])
        assert "Ensemble" in ens.name
        assert "MLP" in ens.name
        assert "GPR" in ens.name


class TestCreateModel:
    def test_mlp_default(self):
        m = create_model("mlp")
        assert isinstance(m, MLPSurrogate)
        assert m.hidden_layer_sizes == (256, 128, 64)

    def test_mlp_custom(self):
        m = create_model("mlp", hidden_layer_sizes=(32, 16), max_iter=100)
        assert isinstance(m, MLPSurrogate)
        assert m.hidden_layer_sizes == (32, 16)
        assert m.max_iter == 100

    def test_gpr(self):
        m = create_model("gpr", alpha=1e-4)
        assert isinstance(m, GPRSurrogate)
        assert m.alpha == 1e-4

    def test_unknown_model(self):
        with pytest.raises(ValueError, match="Unknown model"):
            create_model("xgboost")

    def test_registry_has_mlp_gpr(self):
        assert "mlp" in _MODEL_REGISTRY
        assert "gpr" in _MODEL_REGISTRY
