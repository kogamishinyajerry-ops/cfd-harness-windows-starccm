"""
Surrogate module — CST airfoil parameterization + FFD 3D blade deformation
+ LHS design-of-experiments sampling + watertight-STL builder.

Submodules (solver-agnostic, pure Python + numpy/scikit-learn; M3 track):

  cst       — 12-coefficient 2D airfoil (Bernstein basis, Kulfan 2008)
  ffd       — 5x5x5 tensor-product lattice + bend/twist/translate
  lhs       — Latin Hypercube Sampling of the 12-dim CST design space
              (reads bounds from knowledge/gold_standards/rotor37_cst_baseline.yaml)
  builder   — CST 12-vector -> watertight 1-passage STL (trimesh + shapely)
  data      — SurrogateDataset, Normalizer, split_train_val_test (M3-S3)
  models    — MLPSurrogate, GPRSurrogate, EnsembleSurrogate (M3-S3)
  metrics   — R², MAE, RMSE, coverage_ratio evaluation (M3-S4)
  train     — End-to-end training pipeline + CLI (M3-S3/S4)
  optimize  — NSGA-II multi-objective Pareto optimization (M3-S5)

High-level API:
    cfd_harness.surrogate.CSTAirfoil.from_vector(vec)  # 12 floats -> 2D outline
    cfd_harness.surrogate.FFDBlade.default_unit()       # 5x5x5 unit lattice
    cfd_harness.surrogate.sample_lhs(n, lb, ub)         # (N, 12) LHS samples
    cfd_harness.surrogate.build_watertight_stl(coeffs)   # 12 floats -> trimesh
    cfd_harness.surrogate.generate_mock_data(n=100)      # synthetic dataset
    cfd_harness.surrogate.train(config)                  # full training pipeline
    cfd_harness.surrogate.optimize_pareto(model, norm)   # NSGA-II Pareto front

No STAR-CCM+ coupling here — all submodules are pure Python.
"""
from .cst import (
    CSTAirfoil,
    bernstein,
    cst_class,
    cst_shape,
    vector_to_airfoil,
    airfoil_to_vector,
    N_VARS,
    N_COEFF_LOWER,
    N_COEFF_UPPER,
    N1_DEFAULT,
    N2_DEFAULT,
    DEFAULT_LOWER,
    DEFAULT_UPPER,
)
from .ffd import (
    FFDBlade,
    make_lattice,
    deform_points,
    lattice_to_vector,
    vector_to_lattice,
    bend_lattice,
    twist_lattice,
    translate_lattice,
    DEFAULT_NU,
    DEFAULT_NV,
    DEFAULT_NW,
    DEFAULT_N_CTRL,
    N_DIM,
)
# Re-export the high-level functions so callers can do
#   from cfd_harness.surrogate import sample_lhs, build_watertight_stl, ...
from .lhs import (
    load_lhs_bounds,
    sample_lhs,
    write_lhs_outputs,
    DEFAULT_BASELINE_YAML as DEFAULT_LHS_BASELINE_YAML,
)
from .builder import (
    load_cst_coefficients,
    build_watertight_stl,
    verify_watertight,
    export_stl,
    HUB_RADIUS_M,
    EXTRUDE_M,
    N_OUTLINE_POINTS,
    CHORD_M_DEFAULT,
)
from .data import (
    SurrogateDataset,
    Normalizer,
    split_train_val_test,
    save_dataset,
    load_dataset,
    generate_mock_data,
)
from .models import (
    BaseSurrogate,
    MLPSurrogate,
    GPRSurrogate,
    EnsembleSurrogate,
    create_model,
)
from .metrics import (
    r2 as r2_score,
    mae,
    rmse,
    max_error,
    relative_error,
    coverage_ratio,
    evaluate_per_output,
    evaluate_all,
    parity_summary,
)
from .train import (
    TrainingConfig,
    TrainingResult,
    train,
    load_run,
)
from .optimize import (
    ParetoFront,
    SurrogateOptimizationProblem,
    optimize_pareto,
    optimize_from_training,
    hypervolume,
    compare_fronts,
    DEFAULT_BOUNDS_LOWER as OPT_DEFAULT_BOUNDS_LOWER,
    DEFAULT_BOUNDS_UPPER as OPT_DEFAULT_BOUNDS_UPPER,
    BASELINE_COEFFS,
)

__all__ = [
    # CST
    "CSTAirfoil",
    "bernstein",
    "cst_class",
    "cst_shape",
    "vector_to_airfoil",
    "airfoil_to_vector",
    "N_VARS",
    "N_COEFF_LOWER",
    "N_COEFF_UPPER",
    "N1_DEFAULT",
    "N2_DEFAULT",
    "DEFAULT_LOWER",
    "DEFAULT_UPPER",
    # FFD
    "FFDBlade",
    "make_lattice",
    "deform_points",
    "lattice_to_vector",
    "vector_to_lattice",
    "bend_lattice",
    "twist_lattice",
    "translate_lattice",
    "DEFAULT_NU",
    "DEFAULT_NV",
    "DEFAULT_NW",
    "DEFAULT_N_CTRL",
    "N_DIM",
    # LHS
    "load_lhs_bounds",
    "sample_lhs",
    "write_lhs_outputs",
    "DEFAULT_LHS_BASELINE_YAML",
    # Builder
    "load_cst_coefficients",
    "build_watertight_stl",
    "verify_watertight",
    "export_stl",
    "HUB_RADIUS_M",
    "EXTRUDE_M",
    "N_OUTLINE_POINTS",
    "CHORD_M_DEFAULT",
    # Data (M3-S3)
    "SurrogateDataset",
    "Normalizer",
    "split_train_val_test",
    "save_dataset",
    "load_dataset",
    "generate_mock_data",
    # Models (M3-S3)
    "BaseSurrogate",
    "MLPSurrogate",
    "GPRSurrogate",
    "EnsembleSurrogate",
    "create_model",
    # Metrics (M3-S4)
    "r2_score",
    "mae",
    "rmse",
    "max_error",
    "relative_error",
    "coverage_ratio",
    "evaluate_per_output",
    "evaluate_all",
    "parity_summary",
    # Training (M3-S3/S4)
    "TrainingConfig",
    "TrainingResult",
    "train",
    "load_run",
    # Optimization (M3-S5)
    "ParetoFront",
    "SurrogateOptimizationProblem",
    "optimize_pareto",
    "optimize_from_training",
    "hypervolume",
    "compare_fronts",
    "OPT_DEFAULT_BOUNDS_LOWER",
    "OPT_DEFAULT_BOUNDS_UPPER",
    "BASELINE_COEFFS",
]
