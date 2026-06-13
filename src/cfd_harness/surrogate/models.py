"""
models.py -- Surrogate model definitions (M3-S3).

Neural surrogates for 12-dim CST coefficient → (Cl, Cd) regression.
Fully solver-agnostic: pure Python + sklearn.

Architecture choices for v1:
- MLPSurrogate     — sklearn MLPRegressor, production workhorse
- GPRSurrogate     — Gaussian Process with RBF kernel, uncertainty-aware

Both share the same `BaseSurrogate` interface so the training pipeline
(`train.py`) can swap them without changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import numpy as np


# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class BaseSurrogate(ABC):
    """Abstract surrogate model: 12-dim CST → 2-dim (Cl, Cd)."""

    @abstractmethod
    def fit(self, X: np.ndarray, Y: np.ndarray) -> "BaseSurrogate":
        """Train on (N, 12) inputs, (N, 2) targets."""
        ...

    @abstractmethod
    def predict(self, X: np.ndarray) -> np.ndarray:
        """Return (M, 2) predictions for (M, 12) inputs."""
        ...

    def predict_single(self, coeffs: np.ndarray) -> np.ndarray:
        """Convenience: 12-vector → 2-vector prediction."""
        assert coeffs.shape == (12,), f"Expected (12,), got {coeffs.shape}"
        return self.predict(coeffs.reshape(1, -1))[0]

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable model identifier."""
        ...

    def get_params(self) -> Dict[str, Any]:
        """Return a serializable dict of model hyperparameters."""
        return {}

    def get_metadata(self) -> Dict[str, Any]:
        """Return extra metadata (training time, data size, etc.)."""
        return {}


# ---------------------------------------------------------------------------
# MLP Surrogate (sklearn)
# ---------------------------------------------------------------------------

class MLPSurrogate(BaseSurrogate):
    """Multi-layer perceptron regression surrogate.

    Default architecture: (256, 128, 64) with ReLU, adaptive learning rate.
    This is a practical workhorse for 12→2 regression: trains in seconds
    on 100+ samples, good generalization.

    Parameters:
        hidden_layer_sizes: tuple of layer widths (default (256, 128, 64))
        max_iter: max training iterations (default 2000)
        early_stopping: use val split for early stop (default True)
        alpha: L2 regularization (default 1e-4)
        random_state: reproducibility seed
    """

    def __init__(
        self,
        hidden_layer_sizes: tuple = (256, 128, 64),
        max_iter: int = 2000,
        early_stopping: bool = True,
        alpha: float = 1e-4,
        random_state: int = 42,
        **kwargs,
    ):
        self.hidden_layer_sizes = hidden_layer_sizes
        self.max_iter = max_iter
        self.early_stopping = early_stopping
        self.alpha = alpha
        self.random_state = random_state
        self._kwargs = kwargs
        self._model = None
        self._fitted = False

    @property
    def name(self) -> str:
        layers = "x".join(str(w) for w in self.hidden_layer_sizes)
        return f"MLP({layers})"

    def get_params(self) -> Dict[str, Any]:
        return {
            "hidden_layer_sizes": list(self.hidden_layer_sizes),
            "max_iter": self.max_iter,
            "early_stopping": self.early_stopping,
            "alpha": self.alpha,
            "random_state": self.random_state,
        }

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "MLPSurrogate":
        from sklearn.neural_network import MLPRegressor

        self._model = MLPRegressor(
            hidden_layer_sizes=self.hidden_layer_sizes,
            activation="relu",
            solver="adam",
            max_iter=self.max_iter,
            early_stopping=self.early_stopping,
            validation_fraction=0.15 if self.early_stopping else 0.0,
            alpha=self.alpha,
            random_state=self.random_state,
            **self._kwargs,
        )
        self._model.fit(X, Y)
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("MLPSurrogate not fitted")
        return self._model.predict(X)

    def get_metadata(self) -> Dict[str, Any]:
        if not self._fitted:
            return {}
        return {
            "n_iter": int(self._model.n_iter_),
            "n_layers": int(self._model.n_layers_),
            "loss": float(self._model.loss_),
            "best_validation_score": (
                float(self._model.best_validation_score_)
                if self.early_stopping
                else None
            ),
        }


# ---------------------------------------------------------------------------
# Gaussian Process Surrogate (sklearn)
# ---------------------------------------------------------------------------

class GPRSurrogate(BaseSurrogate):
    """Gaussian Process regression surrogate with RBF kernel.

    Lower-N regime (< 500 samples): GPR excels at interpolation and provides
    built-in uncertainty (std on predictions). For >500 samples, prefer MLP.

    Parameters:
        alpha: noise level for numerical stability (default 1e-6)
        normalize_y: normalize targets before fitting (default True)
        random_state: reproducibility seed
    """

    def __init__(
        self,
        alpha: float = 1e-6,
        normalize_y: bool = True,
        random_state: int = 42,
        **kwargs,
    ):
        self.alpha = alpha
        self.normalize_y = normalize_y
        self.random_state = random_state
        self._kwargs = kwargs
        self._model = None
        self._fitted = False

    @property
    def name(self) -> str:
        return "GPR(RBF)"

    def get_params(self) -> Dict[str, Any]:
        return {
            "alpha": self.alpha,
            "normalize_y": self.normalize_y,
            "random_state": self.random_state,
        }

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "GPRSurrogate":
        from sklearn.gaussian_process import GaussianProcessRegressor
        from sklearn.gaussian_process.kernels import RBF, WhiteKernel

        kernel = RBF(length_scale=1.0) + WhiteKernel(noise_level=self.alpha)
        self._model = GaussianProcessRegressor(
            kernel=kernel,
            alpha=self.alpha,
            normalize_y=self.normalize_y,
            random_state=self.random_state,
            **self._kwargs,
        )
        self._model.fit(X, Y)
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("GPRSurrogate not fitted")
        return self._model.predict(X)

    def predict_with_std(self, X: np.ndarray) -> tuple:
        """Return (mean, std) — std gives prediction uncertainty."""
        if not self._fitted:
            raise RuntimeError("GPRSurrogate not fitted")
        mean, std = self._model.predict(X, return_std=True)
        return mean, std

    def get_metadata(self) -> Dict[str, Any]:
        if not self._fitted:
            return {}
        return {
            "kernel": str(self._model.kernel_),
            "log_marginal_likelihood": float(self._model.log_marginal_likelihood_value_),
        }


# ---------------------------------------------------------------------------
# Ensemble (combine multiple surrogates)
# ---------------------------------------------------------------------------

class EnsembleSurrogate(BaseSurrogate):
    """Average predictions from multiple surrogate models.

    Usage:
        e = EnsembleSurrogate([mlp, gpr])
        e.fit(X_train, Y_train)
        preds = e.predict(X_test)
    """

    def __init__(self, models: list):
        self._models = models
        self._fitted = False

    @property
    def name(self) -> str:
        inner = "+".join(m.name for m in self._models)
        return f"Ensemble({inner})"

    def get_params(self) -> Dict[str, Any]:
        return {"models": [m.get_params() for m in self._models]}

    def fit(self, X: np.ndarray, Y: np.ndarray) -> "EnsembleSurrogate":
        for model in self._models:
            model.fit(X, Y)
        self._fitted = True
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        if not self._fitted:
            raise RuntimeError("EnsembleSurrogate not fitted")
        preds = np.stack([m.predict(X) for m in self._models], axis=0)
        return preds.mean(axis=0)

    def get_metadata(self) -> Dict[str, Any]:
        return {m.name: m.get_metadata() for m in self._models}


# ---------------------------------------------------------------------------
# Model factory
# ---------------------------------------------------------------------------

_MODEL_REGISTRY: Dict[str, type] = {
    "mlp": MLPSurrogate,
    "gpr": GPRSurrogate,
}


def create_model(name: str, **kwargs) -> BaseSurrogate:
    """Create a surrogate model by name.

    Supported: 'mlp', 'gpr'.
    Example: create_model('mlp', hidden_layer_sizes=(128, 64))
    """
    name = name.lower().strip()
    if name not in _MODEL_REGISTRY:
        raise ValueError(
            f"Unknown model '{name}'. Available: {list(_MODEL_REGISTRY.keys())}"
        )
    return _MODEL_REGISTRY[name](**kwargs)


__all__ = [
    "BaseSurrogate",
    "MLPSurrogate",
    "GPRSurrogate",
    "EnsembleSurrogate",
    "create_model",
    "_MODEL_REGISTRY",
]
