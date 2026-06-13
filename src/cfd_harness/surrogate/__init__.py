"""
Surrogate module — CST airfoil parameterization + FFD 3D blade deformation
+ LHS design-of-experiments sampling + watertight-STL builder.

Submodules (solver-agnostic, pure Python + numpy; M3 surrogate track):

  cst       — 12-coefficient 2D airfoil (Bernstein basis, Kulfan 2008)
  ffd       — 5x5x5 tensor-product lattice + bend/twist/translate
  lhs       — Latin Hypercube Sampling of the 12-dim CST design space
              (reads bounds from knowledge/gold_standards/rotor37_cst_baseline.yaml)
  builder   — CST 12-vector -> watertight 1-passage STL (trimesh + shapely)

High-level API:
    cfd_harness.surrogate.CSTAirfoil.from_vector(vec)  # 12 floats -> 2D outline
    cfd_harness.surrogate.FFDBlade.default_unit()       # 5x5x5 unit lattice
    cfd_harness.surrogate.lhs.sample_lhs(n, lb, ub)     # (N, 12) LHS samples
    cfd_harness.surrogate.builder.build_watertight_stl(coeffs)
                                                       # 12 floats -> trimesh

No STAR-CCM+ coupling here. The scripts/ wrappers (scripts/cst_lhs.py,
scripts/build_r37_from_cst.py, scripts/generate_100_stls.py) are thin
CLI front-ends over these modules.
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
]
