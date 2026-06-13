"""
data.py -- Surrogate dataset loading, normalization, train/test split.

M3-S3: Neural surrogate training needs a clean data pipeline to go from
raw (N, 12) CST coefficients + (N, 2) Cl/Cd targets → model-ready tensors.

Design:
- `SurrogateDataset` is a plain dataclass; no torch/pandas dependency.
- `Normalizer` uses pure numpy (mean/std) so training is reproducible.
- `generate_mock_data` creates plausible CST-Cd/Cl pairs for smoke tests
  (12-dim LHS input → monotonic paraboloid targets → 2 outputs).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np


# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------

@dataclass
class SurrogateDataset:
    """(N, 12) CST inputs → (N, 2) Cl/Cd targets.

    Attributes:
        inputs: (N, 12) float64, CST coefficients
        targets: (N, 2) float64, [Cl, Cd]
        feature_names: labels for the 12 CST dims
        target_names: labels for the 2 outputs
        meta: arbitrary metadata dict (case_id, solver_version, etc.)
    """
    inputs: np.ndarray
    targets: np.ndarray
    feature_names: Tuple[str, ...] = field(
        default=("A1_lower", "A2_lower", "A3_lower", "A4_lower", "A5_lower", "A6_lower",
                 "A7_upper", "A8_upper", "A9_upper", "A10_upper", "A11_upper", "A12_upper")
    )
    target_names: Tuple[str, str] = ("Cl", "Cd")
    meta: dict = field(default_factory=dict)

    @property
    def n_samples(self) -> int:
        return self.inputs.shape[0]

    @property
    def n_features(self) -> int:
        return self.inputs.shape[1]

    @property
    def n_targets(self) -> int:
        return self.targets.shape[1]

    def __repr__(self) -> str:
        return (
            f"SurrogateDataset(n={self.n_samples}, "
            f"features={self.n_features}, targets={self.n_targets}"
            + (f", meta_keys={list(self.meta.keys())}" if self.meta else "")
            + ")"
        )

    def validate(self) -> None:
        """Check invariants; raise ValueError on violation."""
        if self.inputs.ndim != 2 or self.inputs.shape[1] != 12:
            raise ValueError(
                f"inputs must be (N, 12), got {self.inputs.shape}"
            )
        if self.targets.ndim != 2 or self.targets.shape[1] != 2:
            raise ValueError(
                f"targets must be (N, 2), got {self.targets.shape}"
            )
        if len(self.inputs) != len(self.targets):
            raise ValueError(
                f"inputs[{len(self.inputs)}] and targets[{len(self.targets)}] "
                f"must have same length"
            )
        if not np.isfinite(self.inputs).all():
            raise ValueError("inputs contain NaN/inf")
        if not np.isfinite(self.targets).all():
            raise ValueError("targets contain NaN/inf")


# ---------------------------------------------------------------------------
# Normalizer (fit-once, apply to train + val + test)
# ---------------------------------------------------------------------------

class Normalizer:
    """Fit (mean, std) on data once; apply to any split."""

    def __init__(self):
        self._input_mean: Optional[np.ndarray] = None
        self._input_std: Optional[np.ndarray] = None
        self._target_mean: Optional[np.ndarray] = None
        self._target_std: Optional[np.ndarray] = None

    def fit(self, dataset: SurrogateDataset) -> "Normalizer":
        self._input_mean = dataset.inputs.mean(axis=0, keepdims=False)
        self._input_std = dataset.inputs.std(axis=0, keepdims=False)
        self._target_mean = dataset.targets.mean(axis=0, keepdims=False)
        self._target_std = dataset.targets.std(axis=0, keepdims=False)
        # Protect zero-std features
        self._input_std[self._input_std < 1e-12] = 1.0
        self._target_std[self._target_std < 1e-12] = 1.0
        return self

    def transform_inputs(self, X: np.ndarray) -> np.ndarray:
        self._check_fit()
        return (X - self._input_mean) / self._input_std

    def transform_targets(self, Y: np.ndarray) -> np.ndarray:
        self._check_fit()
        return (Y - self._target_mean) / self._target_std

    def inverse_transform_targets(self, Y_norm: np.ndarray) -> np.ndarray:
        self._check_fit()
        return Y_norm * self._target_std + self._target_mean

    def _check_fit(self) -> None:
        if self._input_mean is None:
            raise RuntimeError("Normalizer not fitted yet. Call .fit() first.")

    @property
    def input_mean(self) -> np.ndarray:
        self._check_fit()
        return self._input_mean

    @property
    def input_std(self) -> np.ndarray:
        self._check_fit()
        return self._input_std

    @property
    def target_mean(self) -> np.ndarray:
        self._check_fit()
        return self._target_mean

    @property
    def target_std(self) -> np.ndarray:
        self._check_fit()
        return self._target_std


# ---------------------------------------------------------------------------
# Train / val / test split
# ---------------------------------------------------------------------------

def split_train_val_test(
    dataset: SurrogateDataset,
    train_frac: float = 0.7,
    val_frac: float = 0.15,
    seed: int = 42,
) -> Tuple[SurrogateDataset, SurrogateDataset, SurrogateDataset]:
    """Deterministic random split into train/val/test.

    If train_frac + val_frac >= 1.0, test is empty.
    """
    n = dataset.n_samples
    rng = np.random.RandomState(seed)
    idx = rng.permutation(n)

    n_train = max(1, int(n * train_frac))
    n_val = max(0, int(n * val_frac))
    n_test = n - n_train - n_val

    splits = []
    meta_copy = dataset.meta.copy() if dataset.meta else {}
    for start, size in [(0, n_train), (n_train, n_val), (n_train + n_val, n_test)]:
        if size == 0:
            splits.append(None)
            continue
        batch_idx = idx[start : start + size]
        splits.append(
            SurrogateDataset(
                inputs=dataset.inputs[batch_idx].copy(),
                targets=dataset.targets[batch_idx].copy(),
                feature_names=dataset.feature_names,
                target_names=dataset.target_names,
                meta={**meta_copy, "n_original": n, "split_size": size},
            )
        )
    return splits[0], splits[1], splits[2]


# ---------------------------------------------------------------------------
# I/O
# ---------------------------------------------------------------------------

def save_dataset(dataset: SurrogateDataset, path: str) -> None:
    """Write dataset as npz + sidecar json."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    np.savez_compressed(
        path,
        inputs=dataset.inputs,
        targets=dataset.targets,
    )
    # Sidecar metadata
    meta_path = path.replace(".npz", "_meta.json")
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "feature_names": list(dataset.feature_names),
                "target_names": list(dataset.target_names),
                **dataset.meta,
            },
            f,
            indent=2,
        )


def load_dataset(path: str) -> SurrogateDataset:
    """Load dataset from npz (with optional _meta.json sidecar)."""
    data = np.load(path)
    meta = {}
    meta_path = path.replace(".npz", "_meta.json")
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        feature_names = tuple(raw.pop("feature_names", SurrogateDataset.feature_names))
        target_names = tuple(raw.pop("target_names", SurrogateDataset.target_names))
        meta = raw
    else:
        feature_names = SurrogateDataset.feature_names
        target_names = SurrogateDataset.target_names

    ds = SurrogateDataset(
        inputs=data["inputs"],
        targets=data["targets"],
        feature_names=feature_names,
        target_names=target_names,
        meta=meta,
    )
    ds.validate()
    return ds


# ---------------------------------------------------------------------------
# Mock data generator (for smoke tests when real solver data isn't available)
# ---------------------------------------------------------------------------

def generate_mock_data(
    n_samples: int = 100,
    seed: int = 42,
    noise_std: float = 0.02,
) -> SurrogateDataset:
    """Generate plausible synthetic CST→Cl/Cd data.

    The mock target function is a smooth parabolic combination of the 12 inputs
    plus small random noise, producing values in roughly aerodynamic ranges:
    Cl ∈ [0.2, 0.8], Cd ∈ [0.01, 0.05].
    """
    rng = np.random.RandomState(seed)

    # 12-dim LHS-like uniform inputs in [-0.15, 0.15] range (typical CST bounds)
    inputs = rng.uniform(-0.15, 0.15, size=(n_samples, 12))

    # Smooth monotonic response: weighted sum of inputs + nonlinear coupling
    weights = np.linspace(1.5, 0.5, 12)  # earlier coeffs more influential
    linear = inputs @ weights  # (N,)

    # Nonlinear term: quadratic coupling between adjacent coeff pairs
    nonlinear = np.zeros(n_samples)
    for i in range(0, 12, 2):
        nonlinear += inputs[:, i] * inputs[:, i + 1] * 0.5

    # Two outputs with different behaviors
    cl_raw = 0.5 + 0.3 * np.tanh(linear + nonlinear)
    cd_raw = 0.03 + 0.015 * np.abs(linear)  # drag always positive

    cl = cl_raw + rng.normal(0, noise_std, n_samples)
    cd = cd_raw + rng.normal(0, noise_std * 0.5, n_samples)  # less noise on Cd

    targets = np.column_stack([cl, cd])

    return SurrogateDataset(
        inputs=inputs,
        targets=targets,
        meta={
            "generator": "generate_mock_data",
            "seed": seed,
            "noise_std": noise_std,
            "n_samples": n_samples,
        },
    )


__all__ = [
    "SurrogateDataset",
    "Normalizer",
    "split_train_val_test",
    "save_dataset",
    "load_dataset",
    "generate_mock_data",
]
