"""
optimize.py — Multi-objective surrogate-based optimization (M3-S5).

Uses NSGA-II (via pymoo) to find the Pareto front of (Cl, Cd) by
sampling the 12-dim CST design space through a trained surrogate model.

Solver-agnostic: the surrogate model replaces STAR-CCM+ during optimization.
When real solver data arrives, retrain the surrogate and re-run optimization.

Architecture:
  - SurrogateOptimizationProblem  — pymoo Problem wrapping cfd_harness surrogate
  - optimize_pareto()             — run NSGA-II, return ParetoFront
  - ParetoFront                   — results + summary + export
  - CLI                           — python -m cfd_harness.surrogate.optimize
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .data import Normalizer
from .models import BaseSurrogate


# ---------------------------------------------------------------------------
# CST coefficient bounds (from rotor37_cst_baseline.yaml)
# ---------------------------------------------------------------------------

DEFAULT_BOUNDS_LOWER = np.array(
    [-0.15] * 6 + [-0.15] * 6, dtype=np.float64
)
DEFAULT_BOUNDS_UPPER = np.array(
    [0.15] * 6 + [0.15] * 6, dtype=np.float64
)

# Baseline CST coefficients (Rotor37 hub section)
BASELINE_COEFFS = np.array(
    [
        0.1719, 0.1542, 0.1513, 0.1491, 0.1470, 0.1471,
        -0.1719, -0.1498, -0.1498, -0.1495, -0.1491, -0.1485,
    ],
    dtype=np.float64,
)


def load_bounds_from_yaml(yaml_path: str) -> Tuple[np.ndarray, np.ndarray]:
    """Load CST bounds from a knowledge/gold_standards YAML file."""
    import yaml
    with open(yaml_path, encoding="utf-8") as f:
        d = yaml.safe_load(f)
    lb = np.array(d.get("lower_bounds", d.get("lb", DEFAULT_BOUNDS_LOWER)), dtype=np.float64)
    ub = np.array(d.get("upper_bounds", d.get("ub", DEFAULT_BOUNDS_UPPER)), dtype=np.float64)
    assert lb.shape == (12,) and ub.shape == (12,), f"Bounds must be (12,), got {lb.shape}, {ub.shape}"
    return lb, ub


# ============================================================================
# Pareto Front
# ============================================================================

@dataclass
class ParetoFront:
    """Result of a multi-objective optimization run.

    Attributes:
        solutions: (n_pareto, 12) — CST coefficient vectors on the Pareto front
        objectives: (n_pareto, 2) — [Cl, Cd] for each solution
        n_generations: number of NSGA-II generations executed
        elapsed_s: wall-clock time
    """
    solutions: np.ndarray
    objectives: np.ndarray
    n_generations: int = 0
    elapsed_s: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def n_pareto(self) -> int:
        return self.solutions.shape[0]

    @property
    def best_cl(self) -> float:
        """Maximum lift coefficient on the Pareto front."""
        return float(self.objectives[:, 0].max())

    @property
    def best_cd(self) -> float:
        """Minimum drag coefficient on the Pareto front."""
        return float(self.objectives[:, 1].min())

    @property
    def summary(self) -> Dict[str, Any]:
        return {
            "n_pareto": self.n_pareto,
            "n_generations": self.n_generations,
            "elapsed_s": round(self.elapsed_s, 3),
            "Cl_range": [round(float(self.objectives[:, 0].min()), 6),
                         round(float(self.objectives[:, 0].max()), 6)],
            "Cd_range": [round(float(self.objectives[:, 1].min()), 6),
                         round(float(self.objectives[:, 1].max()), 6)],
            "best_Cl": round(self.best_cl, 6),
            "best_Cd": round(self.best_cd, 6),
        }

    def get_knee_point(self) -> np.ndarray:
        """Heuristic knee-point: solution closest to the ideal point (max Cl, min Cd)."""
        ideal = np.array([self.objectives[:, 0].max(), self.objectives[:, 1].min()])
        distances = np.linalg.norm(self.objectives - ideal, axis=1)
        idx = np.argmin(distances)
        return self.solutions[idx]

    def export(self, path: str) -> None:
        """Export Pareto front to npz + json."""
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(out, solutions=self.solutions, objectives=self.objectives)
        meta_path = out.with_suffix(".json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.summary, f, indent=2)


# ============================================================================
# Surrogate Optimization Problem (pymoo interface)
# ============================================================================

class SurrogateOptimizationProblem:
    """Wrap a trained surrogate as a pymoo Problem for NSGA-II.

    The surrogate maps 12 CST coeffs → [Cl, Cd].
    NSGA-II minimizes both objectives → we minimize [-Cl, Cd]
    so that maximizing Cl becomes minimizing -Cl.

    NOTE: This is a plain Python class, NOT a pymoo Problem subclass,
    to keep the import lazy (pymoo is optional). The _to_pymoo() method
    returns the actual pymoo Problem when needed.
    """

    def __init__(
        self,
        surrogate: BaseSurrogate,
        normalizer: Normalizer,
        bounds_lower: np.ndarray,
        bounds_upper: np.ndarray,
        n_var: int = 12,
        n_obj: int = 2,
    ):
        self.surrogate = surrogate
        self.normalizer = normalizer
        self.xl = np.asarray(bounds_lower, dtype=np.float64)
        self.xu = np.asarray(bounds_upper, dtype=np.float64)
        self.n_var = n_var
        self.n_obj = n_obj

    def evaluate(self, X: np.ndarray) -> np.ndarray:
        """Evaluate (N, 12) CST vectors → (N, 2) objectives.

        objectives[:, 0] = -Cl  (minimize → maximize lift)
        objectives[:, 1] = Cd   (minimize → minimize drag)
        """
        X_norm = self.normalizer.transform_inputs(X)
        Y_pred_norm = self.surrogate.predict(X_norm)
        Y_pred = self.normalizer.inverse_transform_targets(Y_pred_norm)

        cl = Y_pred[:, 0]
        cd = Y_pred[:, 1]

        # Objective 1: maximize lift → minimize -Cl
        # Objective 2: minimize drag → minimize Cd
        return np.column_stack([-cl, cd])

    def _to_pymoo(self, seed: int = 42):
        """Convert to pymoo Problem. Returns (problem, algorithm, termination)."""
        from pymoo.core.problem import ElementwiseProblem

        class _PymooProblem(ElementwiseProblem):
            def __init__(_self, parent):
                super().__init__(
                    n_var=parent.n_var,
                    n_obj=parent.n_obj,
                    xl=parent.xl,
                    xu=parent.xu,
                )
                _self._parent = parent

            def _evaluate(_self, x, out, *args, **kwargs):
                f = _self._parent.evaluate(x.reshape(1, -1))
                out["F"] = f[0]

        return _PymooProblem(self)


# ============================================================================
# NSGA-II Optimization
# ============================================================================

def optimize_pareto(
    surrogate: BaseSurrogate,
    normalizer: Normalizer,
    bounds_lower: Optional[np.ndarray] = None,
    bounds_upper: Optional[np.ndarray] = None,
    pop_size: int = 200,
    n_generations: int = 100,
    seed: int = 42,
    verbose: bool = False,
) -> ParetoFront:
    """Run NSGA-II multi-objective optimization on the surrogate.

    Args:
        surrogate: trained surrogate model (MLP or GPR)
        normalizer: fitted Normalizer from training
        bounds_lower: (12,) lower bounds (default: -0.15)
        bounds_upper: (12,) upper bounds (default: 0.15)
        pop_size: population size (default 200)
        n_generations: NSGA-II generations (default 100)
        seed: random seed
        verbose: print progress

    Returns:
        ParetoFront with solutions, objectives, and summary.
    """
    from pymoo.algorithms.moo.nsga2 import NSGA2
    from pymoo.operators.crossover.sbx import SBX
    from pymoo.operators.mutation.pm import PM
    from pymoo.operators.sampling.rnd import FloatRandomSampling
    from pymoo.optimize import minimize
    from pymoo.termination import get_termination

    if bounds_lower is None:
        bounds_lower = DEFAULT_BOUNDS_LOWER.copy()
    if bounds_upper is None:
        bounds_upper = DEFAULT_BOUNDS_UPPER.copy()

    problem_wrapper = SurrogateOptimizationProblem(
        surrogate=surrogate,
        normalizer=normalizer,
        bounds_lower=bounds_lower,
        bounds_upper=bounds_upper,
    )

    problem = problem_wrapper._to_pymoo(seed=seed)

    algorithm = NSGA2(
        pop_size=pop_size,
        sampling=FloatRandomSampling(),
        crossover=SBX(prob=0.9, eta=15),
        mutation=PM(prob=1.0 / 12, eta=20),
        eliminate_duplicates=True,
    )

    termination = get_termination("n_gen", n_generations)

    t0 = time.perf_counter()
    res = minimize(
        problem,
        algorithm,
        termination,
        seed=seed,
        verbose=verbose,
        save_history=False,
    )
    t1 = time.perf_counter()

    # pymoo stores results in res.X (design) and res.F (objectives)
    solutions = res.X  # (n_pareto, 12)
    objectives = res.F  # (n_pareto, 2) — [-Cl, Cd]

    # Convert objectives back to [Cl, Cd]
    objectives_actual = np.column_stack([-objectives[:, 0], objectives[:, 1]])

    return ParetoFront(
        solutions=solutions,
        objectives=objectives_actual,
        n_generations=n_generations,
        elapsed_s=t1 - t0,
        metadata={
            "pop_size": pop_size,
            "n_generations": n_generations,
            "seed": seed,
            "surrogate_model": surrogate.name,
        },
    )


# ============================================================================
# Quick optimization from a training run
# ============================================================================

def optimize_from_training(
    training_result,
    pop_size: int = 200,
    n_generations: int = 100,
    seed: int = 42,
    verbose: bool = False,
) -> ParetoFront:
    """Convenience: optimize directly from a TrainingResult."""
    return optimize_pareto(
        surrogate=training_result.model,
        normalizer=training_result.normalizer,
        pop_size=pop_size,
        n_generations=n_generations,
        seed=seed,
        verbose=verbose,
    )


# ============================================================================
# Pareto front analysis helpers
# ============================================================================

def hypervolume(pareto: ParetoFront, ref_point: Optional[np.ndarray] = None) -> float:
    """Compute hypervolume indicator (dominated volume).

    Args:
        pareto: ParetoFront to evaluate
        ref_point: reference point [Cl_min, Cd_max]. Default: (0, 0.1).

    Returns:
        hypervolume (larger = better front)
    """
    if ref_point is None:
        ref_point = np.array([0.0, 0.1])
    from pymoo.indicators.hv import Hypervolume
    hv = Hypervolume(ref_point=ref_point)
    # Minimize both: [-Cl, Cd]
    F_norm = np.column_stack([-pareto.objectives[:, 0], pareto.objectives[:, 1]])
    return float(hv(F_norm))


def compare_fronts(
    front_a: ParetoFront,
    front_b: ParetoFront,
    label_a: str = "A",
    label_b: str = "B",
) -> Dict[str, Any]:
    """Compare two Pareto fronts with dominance + hypervolume.

    Returns a dict with per-front stats and comparison.
    """
    ref = np.array([0.0, 0.1])
    hv_a = hypervolume(front_a, ref)
    hv_b = hypervolume(front_b, ref)

    return {
        f"{label_a}_n": front_a.n_pareto,
        f"{label_a}_hypervolume": round(hv_a, 6),
        f"{label_a}_Cl_range": [round(float(front_a.objectives[:, 0].min()), 6),
                                  round(float(front_a.objectives[:, 0].max()), 6)],
        f"{label_a}_Cd_range": [round(float(front_a.objectives[:, 1].min()), 6),
                                  round(float(front_a.objectives[:, 1].max()), 6)],
        f"{label_b}_n": front_b.n_pareto,
        f"{label_b}_hypervolume": round(hv_b, 6),
        f"{label_b}_Cl_range": [round(float(front_b.objectives[:, 0].min()), 6),
                                  round(float(front_b.objectives[:, 0].max()), 6)],
        f"{label_b}_Cd_range": [round(float(front_b.objectives[:, 1].min()), 6),
                                  round(float(front_b.objectives[:, 1].max()), 6)],
        "hypervolume_ratio": round(hv_a / hv_b, 4) if hv_b > 0 else None,
    }


# ============================================================================
# CLI
# ============================================================================

def _cli_main(argv=None):
    import argparse

    p = argparse.ArgumentParser(
        description="M3-S5: NSGA-II multi-objective surrogate optimization"
    )
    p.add_argument("--model", required=True,
                   help="Path to trained .joblib model file")
    p.add_argument("--normalizer", default=None,
                   help="Path to _normalizer.npz (auto-detected from model path)")
    p.add_argument("--pop-size", type=int, default=200)
    p.add_argument("--generations", type=int, default=100)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--output", default="models/surrogate",
                   help="Output directory for Pareto front")
    p.add_argument("--name", default="pareto",
                   help="Output name prefix")

    args = p.parse_args(argv)

    import joblib
    model = joblib.load(args.model)

    norm_path = args.normalizer or args.model.replace(".joblib", "_normalizer.npz")
    norm_data = np.load(norm_path)
    normalizer = Normalizer()
    normalizer._input_mean = norm_data["input_mean"]
    normalizer._input_std = norm_data["input_std"]
    normalizer._target_mean = norm_data["target_mean"]
    normalizer._target_std = norm_data["target_std"]

    result = optimize_pareto(
        surrogate=model,
        normalizer=normalizer,
        pop_size=args.pop_size,
        n_generations=args.generations,
        seed=args.seed,
        verbose=True,
    )

    # Export
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    result.export(str(out_dir / args.name))
    print(f"\nPareto front saved to {out_dir / args.name}.npz")

    # Summary
    print(f"\n{'='*60}")
    print(f"  Pareto Front Summary ({result.surrogate_model})")
    print(f"{'='*60}")
    for k, v in result.summary.items():
        print(f"  {k}: {v}")

    if result.n_pareto >= 3:
        print(f"\n  Top 3 (best Cl):")
        idx = np.argsort(result.objectives[:, 0])[::-1][:3]
        for i in idx:
            print(f"    Cl={result.objectives[i, 0]:.5f}  "
                  f"Cd={result.objectives[i, 1]:.5f}")
        print(f"\n  Top 3 (best Cd):")
        idx = np.argsort(result.objectives[:, 1])[:3]
        for i in idx:
            print(f"    Cl={result.objectives[i, 0]:.5f}  "
                  f"Cd={result.objectives[i, 1]:.5f}")


if __name__ == "__main__":
    _cli_main()


__all__ = [
    "DEFAULT_BOUNDS_LOWER",
    "DEFAULT_BOUNDS_UPPER",
    "BASELINE_COEFFS",
    "load_bounds_from_yaml",
    "ParetoFront",
    "SurrogateOptimizationProblem",
    "optimize_pareto",
    "optimize_from_training",
    "hypervolume",
    "compare_fronts",
]
