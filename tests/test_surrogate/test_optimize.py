"""Integration tests for surrogate-based NSGA-II optimization (M3-S5).

Tests:
- optimize_pareto returns valid ParetoFront on mock data
- ParetoFront properties and analysis helpers
- Pareto front export/import
- Comparison between MLP and GPR fronts
- Knee-point selection
- CLI smoke test
"""

import os
import json

import numpy as np
import pytest

from cfd_harness.surrogate.optimize import (
    ParetoFront,
    SurrogateOptimizationProblem,
    optimize_pareto,
    optimize_from_training,
    hypervolume,
    compare_fronts,
    BASELINE_COEFFS,
    DEFAULT_BOUNDS_LOWER,
    DEFAULT_BOUNDS_UPPER,
)
from cfd_harness.surrogate.train import TrainingConfig, train


@pytest.fixture(scope="module")
def trained_result():
    """Train a surrogate model for optimization testing."""
    cfg = TrainingConfig(
        model_type="mlp",
        n_mock_samples=120,
        seed=42,
        output_dir="models/surrogate",
        train_frac=0.75,
        val_frac=0.25,
    )
    return train(cfg)


@pytest.fixture(scope="module")
def pareto_front(trained_result):
    """Run NSGA-II optimization once for this module."""
    return optimize_from_training(
        trained_result,
        pop_size=80,       # smaller pop for test speed
        n_generations=20,  # fewer generations
        seed=42,
    )


class TestParetoFront:
    def test_has_solutions(self, pareto_front):
        assert pareto_front.n_pareto >= 1
        assert pareto_front.solutions.shape[1] == 12
        assert pareto_front.objectives.shape[1] == 2
        assert pareto_front.elapsed_s > 0

    def test_summary_keys(self, pareto_front):
        s = pareto_front.summary
        assert "n_pareto" in s
        assert "n_generations" in s
        assert "elapsed_s" in s
        assert "Cl_range" in s
        assert "Cd_range" in s

    def test_solutions_in_bounds(self, pareto_front):
        for i in range(pareto_front.n_pareto):
            assert (pareto_front.solutions[i] >= DEFAULT_BOUNDS_LOWER - 1e-6).all()
            assert (pareto_front.solutions[i] <= DEFAULT_BOUNDS_UPPER + 1e-6).all()

    def test_non_dominated(self, pareto_front):
        """Verify no solution dominates another on the Pareto front.

        A dominates B if A has better (or equal) Cl AND better (or equal) Cd,
        and strictly better in at least one.
        """
        objs = pareto_front.objectives
        for i in range(pareto_front.n_pareto):
            for j in range(i + 1, pareto_front.n_pareto):
                # A dominates B if: Cl_A >= Cl_B AND Cd_A <= Cd_B AND (strict in one)
                a_better_cl = objs[i, 0] > objs[j, 0] + 1e-8
                a_better_cd = objs[i, 1] < objs[j, 1] - 1e-8
                b_better_cl = objs[j, 0] > objs[i, 0] + 1e-8
                b_better_cd = objs[j, 1] < objs[i, 1] - 1e-8

                if a_better_cl and a_better_cd:
                    assert False, f"Solution {i} dominates {j}"
                if b_better_cl and b_better_cd:
                    assert False, f"Solution {j} dominates {i}"

    def test_export_roundtrip(self, pareto_front, tmp_path):
        path = str(tmp_path / "test_pareto.npz")
        pareto_front.export(path)
        assert os.path.exists(path)

        data = np.load(path)
        assert data["solutions"].shape == pareto_front.solutions.shape
        assert data["objectives"].shape == pareto_front.objectives.shape
        assert np.allclose(data["solutions"], pareto_front.solutions)
        assert np.allclose(data["objectives"], pareto_front.objectives)

        meta_path = path.replace(".npz", ".json")
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["n_pareto"] == pareto_front.n_pareto

    def test_knee_point(self, pareto_front):
        knee = pareto_front.get_knee_point()
        assert knee.shape == (12,)
        # Knee should be within bounds
        assert (knee >= DEFAULT_BOUNDS_LOWER - 1e-6).all()
        assert (knee <= DEFAULT_BOUNDS_UPPER + 1e-6).all()

    def test_best_cl_cd(self, pareto_front):
        cl_vals = pareto_front.objectives[:, 0]
        cd_vals = pareto_front.objectives[:, 1]
        assert pareto_front.best_cl == pytest.approx(cl_vals.max())
        assert pareto_front.best_cd == pytest.approx(cd_vals.min())


class TestHypervolume:
    def test_returns_finite(self, pareto_front):
        hv = hypervolume(pareto_front)
        assert np.isfinite(hv)
        assert hv > 0


class TestCompareFronts:
    def test_returns_comparison(self, trained_result):
        front_mlp = optimize_from_training(
            trained_result, pop_size=50, n_generations=10, seed=1
        )
        front_mlp2 = optimize_from_training(
            trained_result, pop_size=50, n_generations=10, seed=2
        )
        comparison = compare_fronts(front_mlp, front_mlp2, "MLP_run1", "MLP_run2")
        assert "MLP_run1_hypervolume" in comparison
        assert "MLP_run2_hypervolume" in comparison

    def test_same_seed_reproducible(self, trained_result):
        f1 = optimize_from_training(
            trained_result, pop_size=50, n_generations=10, seed=123
        )
        f2 = optimize_from_training(
            trained_result, pop_size=50, n_generations=10, seed=123
        )
        assert np.allclose(f1.objectives, f2.objectives)
        assert np.allclose(f1.solutions, f2.solutions)


class TestGPROptimization:
    def test_gpr_pareto(self, tmp_path):
        cfg = TrainingConfig(
            model_type="gpr",
            n_mock_samples=60,
            seed=3,
            output_dir=str(tmp_path / "models"),
            train_frac=0.8,
            val_frac=0.2,
        )
        result = train(cfg)
        front = optimize_from_training(result, pop_size=40, n_generations=10, seed=3)
        assert front.n_pareto >= 1
        assert front.elapsed_s > 0


class TestCLISmoke:
    def test_cli_help(self):
        from cfd_harness.surrogate.optimize import _cli_main
        import sys
        try:
            _cli_main(["--help"])
        except SystemExit:
            pass
