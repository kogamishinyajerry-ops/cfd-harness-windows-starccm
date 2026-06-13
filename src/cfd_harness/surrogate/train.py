"""
train.py -- End-to-end surrogate training pipeline (M3-S3/S4).

Fully solver-agnostic: takes (N, 12) CST coefficients + (N, 2) Cl/Cd targets,
trains a model, evaluates, and saves.

Workflow:
  1. Load dataset (npz or generate mock)
  2. Normalize
  3. Split train/val/test
  4. Fit model
  5. Evaluate on all splits
  6. Save model + metrics

CLI:
    python -m cfd_harness.surrogate.train --model mlp --samples 100
    python -m cfd_harness.surrogate.train --model gpr --data my_samples.npz --output my_model
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import numpy as np

from .data import (
    SurrogateDataset,
    Normalizer,
    split_train_val_test,
    generate_mock_data,
    load_dataset,
    save_dataset,
)
from .metrics import evaluate_all, parity_summary, evaluate_per_output
from .models import BaseSurrogate, create_model, GPRSurrogate


# ---------------------------------------------------------------------------
# Training configuration
# ---------------------------------------------------------------------------

@dataclass
class TrainingConfig:
    """All knobs for a training run."""

    model_type: str = "mlp"
    model_kwargs: Dict[str, Any] = field(default_factory=dict)

    # Data
    data_path: Optional[str] = None          # npz file or None → generate mock
    n_mock_samples: int = 100
    mock_noise_std: float = 0.02
    seed: int = 42

    # Split
    train_frac: float = 0.7
    val_frac: float = 0.15

    # Output
    output_dir: str = "models/surrogate"
    model_name: Optional[str] = None          # auto-generated if None

    # Evaluation
    eval_on_train: bool = True
    eval_on_val: bool = True
    eval_on_test: bool = True
    compute_std: bool = False                 # GPR uncertainty (expensive)

    # Signed accuracy audit (reuses the DEC-010 chain via surrogate.vv).
    # OFF by default → no behaviour change. When on, writes
    # <output_dir>/<name>_audit.json, verifiable with
    # `python -m cfd_harness.audit_package.verify`. A mock/synthetic-trained
    # surrogate can never be `validated` (the vv honesty ceiling).
    emit_audit: bool = False
    audit_data_source: Optional[str] = None   # "real"|"mock"; None → inferred
    audit_acceptance: Optional[Any] = None    # vv.SurrogateAcceptance; None → defaults


# ---------------------------------------------------------------------------
# Training result
# ---------------------------------------------------------------------------

@dataclass
class TrainingResult:
    """All artifacts from a training run."""

    model: BaseSurrogate
    normalizer: Normalizer
    config: TrainingConfig
    metrics: Dict[str, Any] = field(default_factory=dict)
    elapsed_s: float = 0.0
    model_path: Optional[str] = None
    audit_path: Optional[str] = None          # set when config.emit_audit

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "model": self.model.name,
            "model_params": self.model.get_params(),
            "model_metadata": self.model.get_metadata(),
            "n_train": self.metrics.get("n_train"),
            "n_val": self.metrics.get("n_val"),
            "n_test": self.metrics.get("n_test"),
            "test_r2": self.metrics.get("test_r2"),
            "test_mae": self.metrics.get("test_mae"),
            "test_rmse": self.metrics.get("test_rmse"),
            "elapsed_s": round(self.elapsed_s, 3),
        }


# ---------------------------------------------------------------------------
# Core training pipeline
# ---------------------------------------------------------------------------

def train(config: TrainingConfig) -> TrainingResult:
    """Run the full training pipeline and return a TrainingResult."""
    t0 = time.perf_counter()

    # 1. Load or generate data
    if config.data_path:
        dataset = load_dataset(config.data_path)
    else:
        dataset = generate_mock_data(
            n_samples=config.n_mock_samples,
            seed=config.seed,
            noise_std=config.mock_noise_std,
        )

    # 2. Split
    train_ds, val_ds, test_ds = split_train_val_test(
        dataset,
        train_frac=config.train_frac,
        val_frac=config.val_frac,
        seed=config.seed,
    )

    # 3. Normalize (fit on train only)
    normalizer = Normalizer()
    normalizer.fit(train_ds)

    X_train = normalizer.transform_inputs(train_ds.inputs)
    Y_train = normalizer.transform_targets(train_ds.targets)

    # 4. Create & fit model
    model = create_model(config.model_type, **config.model_kwargs)
    model.fit(X_train, Y_train)

    # 5. Evaluate
    metrics: Dict[str, Any] = {
        "n_train": train_ds.n_samples,
        "n_val": val_ds.n_samples if val_ds else 0,
        "n_test": test_ds.n_samples if test_ds else 0,
        "model_type": config.model_type,
    }

    splits = [
        ("train", train_ds, config.eval_on_train),
        ("val", val_ds, config.eval_on_val),
        ("test", test_ds, config.eval_on_test),
    ]
    test_true = None  # captured for the optional signed accuracy audit
    test_pred = None
    for label, ds, enabled in splits:
        if not enabled or ds is None:
            continue
        X = normalizer.transform_inputs(ds.inputs)
        Y_pred_norm = model.predict(X)
        Y_pred = normalizer.inverse_transform_targets(Y_pred_norm)
        if label == "test":
            test_true, test_pred = ds.targets, Y_pred

        split_metrics = evaluate_all(ds.targets, Y_pred, label=label)
        metrics.update(split_metrics)

        # Per-output parity
        per_out = evaluate_per_output(ds.targets, Y_pred)
        metrics[f"{label}_per_output"] = per_out

        # GPR uncertainty (optional)
        if config.compute_std and isinstance(model, GPRSurrogate):
            _, Y_std_norm = model.predict_with_std(X)
            Y_std = Y_std_norm * normalizer.target_std  # un-normalize std
            metrics[f"{label}_coverage_2sigma"] = float(
                (np.abs(ds.targets - Y_pred) <= 2.0 * Y_std).mean()
            )

    # 6. Save model artifacts
    t1 = time.perf_counter()
    model_name = config.model_name or f"{config.model_type}_{dataset.n_samples}samples"
    model_path = _save_run(model, normalizer, config, metrics, model_name)

    # 7. Optional signed accuracy audit (DEC-010 chain) — off by default.
    audit_path = None
    if config.emit_audit and test_true is not None:
        audit_path = _emit_surrogate_audit(test_true, test_pred, config, model_name)

    return TrainingResult(
        model=model,
        normalizer=normalizer,
        config=config,
        metrics=metrics,
        elapsed_s=t1 - t0,
        model_path=model_path,
        audit_path=audit_path,
    )


def _emit_surrogate_audit(test_true, test_pred, config: "TrainingConfig", name: str) -> str:
    """Write a signed surrogate-accuracy audit for the held-out test set.

    Lazy imports keep the surrogate package's normal import graph unchanged —
    the audit machinery is only pulled in when emit_audit is requested.
    data_source is inferred (real if a real dataset was provided, else mock)
    unless explicitly set; a mock/synthetic-trained surrogate can never be
    `validated` (the vv honesty ceiling). Verify with
    `python -m cfd_harness.audit_package.verify <path>`.
    """
    from .vv import (
        SurrogateAcceptance,
        build_signed_surrogate_audit,
        evaluate_surrogate,
        DATA_SOURCE_MOCK,
        DATA_SOURCE_REAL,
    )
    from cfd_harness.audit_package.sign import DEV_UNSIGNED_KEY

    data_source = config.audit_data_source or (
        DATA_SOURCE_REAL if config.data_path else DATA_SOURCE_MOCK
    )
    acceptance = config.audit_acceptance or SurrogateAcceptance()
    verdict = evaluate_surrogate(test_true, test_pred, acceptance, data_source=data_source)

    key_env = os.environ.get("CFD_HARNESS_SIGN_KEY")
    if key_env:
        key, key_source = key_env.encode("utf-8"), "provided"
    else:
        key, key_source = DEV_UNSIGNED_KEY, "dev-unsigned"

    audit = build_signed_surrogate_audit(verdict, key, model_id=name, key_source=key_source)
    audit_path = Path(config.output_dir) / f"{name}_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    return str(audit_path)


def _save_run(
    model: BaseSurrogate,
    normalizer: Normalizer,
    config: TrainingConfig,
    metrics: Dict[str, Any],
    name: str,
) -> str:
    """Persist model, normalizer, and metrics to disk."""
    out_dir = Path(config.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Save normalizer (simple npz)
    norm_path = out_dir / f"{name}_normalizer.npz"
    np.savez_compressed(
        norm_path,
        input_mean=normalizer.input_mean,
        input_std=normalizer.input_std,
        target_mean=normalizer.target_mean,
        target_std=normalizer.target_std,
    )

    # Save metrics
    metrics_path = out_dir / f"{name}_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2, default=str)

    # Save model (joblib for sklearn models)
    model_path = out_dir / f"{name}.joblib"
    try:
        import joblib
        joblib.dump(model, model_path)
    except ImportError:
        # Fallback: save to npz (lossy for non-sklearn, but ok for v1)
        np_path = out_dir / f"{name}_model.npz"
        np.savez_compressed(np_path, model_type=model.name)
        model_path = np_path

    return str(model_path)


def load_run(name: str, models_dir: str = "models/surrogate") -> TrainingResult:
    """Load a previously saved TrainingResult from disk.

    Returns a lightweight TrainingResult with model + normalizer loaded.
    """
    import joblib

    base = Path(models_dir)
    model_path = base / f"{name}.joblib"
    norm_path = base / f"{name}_normalizer.npz"
    metrics_path = base / f"{name}_metrics.json"

    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = joblib.load(model_path)

    norm_data = np.load(norm_path)
    normalizer = Normalizer()
    normalizer._input_mean = norm_data["input_mean"]
    normalizer._input_std = norm_data["input_std"]
    normalizer._target_mean = norm_data["target_mean"]
    normalizer._target_std = norm_data["target_std"]

    metrics = {}
    if metrics_path.exists():
        with open(metrics_path, "r", encoding="utf-8") as f:
            metrics = json.load(f)

    config = TrainingConfig(model_type=model.name, model_name=name)

    return TrainingResult(
        model=model,
        normalizer=normalizer,
        config=config,
        metrics=metrics,
        model_path=str(model_path),
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _cli_main(argv=None):
    """Minimal argparse CLI for `python -m cfd_harness.surrogate.train`."""
    import argparse

    p = argparse.ArgumentParser(
        description="M3 surrogate training pipeline (12-dim CST → Cl/Cd)"
    )
    p.add_argument("--model", default="mlp", choices=["mlp", "gpr"],
                   help="Model type (default mlp)")
    p.add_argument("--data", default=None,
                   help="Path to dataset .npz (default: generate mock)")
    p.add_argument("--samples", type=int, default=100,
                   help="Number of mock samples to generate (default 100)")
    p.add_argument("--noise", type=float, default=0.02,
                   help="Mock data noise std (default 0.02)")
    p.add_argument("--output", default="models/surrogate",
                   help="Output directory (default models/surrogate)")
    p.add_argument("--name", default=None,
                   help="Model name (auto-generated if omitted)")
    p.add_argument("--seed", type=int, default=42,
                   help="Random seed (default 42)")
    p.add_argument("--compute-std", action="store_true",
                   help="Compute GPR prediction uncertainty")
    p.add_argument("--hidden", type=int, nargs="+", default=[256, 128, 64],
                   help="MLP hidden layer sizes (default 256 128 64)")
    p.add_argument("--max-iter", type=int, default=2000,
                   help="MLP max iterations (default 2000)")
    p.add_argument("--emit-audit", action="store_true",
                   help="Emit a signed surrogate-accuracy audit (DEC-010); "
                        "set CFD_HARNESS_SIGN_KEY for a trusted audit")
    p.add_argument("--audit-data-source", default=None, choices=["real", "mock"],
                   help="Override audit data_source (default: inferred — real "
                        "if --data given, else mock; mock can never validate)")

    args = p.parse_args(argv)

    config = TrainingConfig(
        model_type=args.model,
        model_kwargs={
            "hidden_layer_sizes": tuple(args.hidden),
            "max_iter": args.max_iter,
        },
        data_path=args.data,
        n_mock_samples=args.samples,
        mock_noise_std=args.noise,
        seed=args.seed,
        output_dir=args.output,
        model_name=args.name,
        compute_std=args.compute_std,
        emit_audit=args.emit_audit,
        audit_data_source=args.audit_data_source,
    )

    result = train(config)

    print(f"\n{'='*60}")
    print(f"  Training complete: {result.model.name}")
    print(f"{'='*60}")
    print(f"  Elapsed:  {result.elapsed_s:.3f}s")
    print(f"  Train:    {result.metrics.get('n_train', '?')} samples")
    print(f"  Val:      {result.metrics.get('n_val', '?')} samples")
    print(f"  Test:     {result.metrics.get('n_test', '?')} samples")
    print(f"  Test R²:  {result.metrics.get('test_r2', 'N/A'):.4f}")
    print(f"  Test MAE: {result.metrics.get('test_mae', 'N/A'):.6f}")
    print(f"  Test RMSE:{result.metrics.get('test_rmse', 'N/A'):.6f}")
    print(f"  Saved:    {result.model_path}")
    if result.audit_path:
        print(f"  Audit:    {result.audit_path}")
    print()

    print("Per-output test metrics:")
    per_out = result.metrics.get("test_per_output", {})
    for out_name, m in per_out.items():
        print(f"  {out_name}: R²={m['r2']:.4f}  MAE={m['mae']:.6f}  "
              f"RMSE={m['rmse']:.6f}  max_err={m['max_error']:.6f}")

    print()
    print(json.dumps(result.summary, indent=2, default=str))


if __name__ == "__main__":
    _cli_main()


__all__ = [
    "TrainingConfig",
    "TrainingResult",
    "train",
    "load_run",
]
