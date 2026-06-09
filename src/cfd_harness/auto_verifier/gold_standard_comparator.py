"""GoldStandardComparator: compares solver key_quantities vs literature-anchored gold.

The HEART of the V&V loop. Per
`docs/specs/EXECUTOR_ABSTRACTION.md` §6.1, the MOCK executor's verdict
ceiling is `WARN` (never `PASS`); real-solver runs (DOCKER_OPENFOAM /
WIN_STARCCM) can reach `PASS` / `WARN` / `FAIL`.

The comparator loads a gold-standard YAML and compares the run's
`key_quantities` against the `reference_values`. The comparison is
solver-agnostic: the gold standard is literature-anchored
(Ghia 1982, Ladson 1988, Williamson 1996, etc.) and the run's
`key_quantities` are what the solver produces at the gold points.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

__all__ = ["GoldStandardComparator", "ComparisonResult", "QuantityResult"]


@dataclass(frozen=True)
class QuantityResult:
    """A single quantity's comparison outcome."""
    name: str
    measured: float
    gold: float
    relative_error: float
    tolerance: float
    all_pass: bool


@dataclass(frozen=True)
class ComparisonResult:
    """The full gold-comparator output.

    `all_pass=True` iff every quantity is within its tolerance.
    `failing_quantities` lists the names of failed quantities.
    """
    all_pass: bool
    quantities: List[QuantityResult] = field(default_factory=list)
    failing_quantities: List[str] = field(default_factory=list)
    tolerance_warnings: List[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.all_pass


class GoldStandardComparator:
    """Compares an ExecutionResult's key_quantities against a gold-standard YAML.

    `tolerance_floor`: the default relative tolerance when the gold
    standard does not specify one. The gold-standard's `tolerance`
    field ALWAYS wins; the floor is just a safety net.
    """
    def __init__(self, tolerance_floor: float = 0.05) -> None:
        if tolerance_floor <= 0:
            raise ValueError(f"tolerance_floor must be > 0, got {tolerance_floor}")
        self.tolerance_floor = tolerance_floor

    def compare(
        self,
        gold_path: Path,
        measured_quantities: Dict[str, Any],
    ) -> ComparisonResult:
        """Compare measured vs gold.

        `gold_path`: path to a `knowledge/gold_standards/<id>.yaml` file.
        `measured_quantities`: the solver run's `key_quantities` dict
        (from `ExecutionResult`).

        The gold standard may have multiple `quantity:` blocks (LDC
        has u_centerline + v_centerline + primary_vortex_location +
        secondary_vortices). Each is compared independently; the
        overall verdict is `all_pass=True` iff every quantity passes.
        """
        if not gold_path.exists():
            return ComparisonResult(
                all_pass=False,
                failing_quantities=["__gold_anchor_missing__"],
            )
        with gold_path.open(encoding="utf-8") as f:
            # A gold-standard file may have multiple `---` documents,
            # one per quantity. Load all of them.
            docs = list(yaml.safe_load_all(f))

        results: List[QuantityResult] = []
        failing: List[str] = []
        warnings: List[str] = []

        for doc in docs:
            if not doc or "quantity" not in doc:
                continue
            qname = doc["quantity"]
            tolerance = float(doc.get("tolerance", self.tolerance_floor))
            ref_values = doc.get("reference_values", [])
            if not ref_values:
                warnings.append(f"gold:{qname}:no_reference_values")
                continue
            measured = measured_quantities.get(qname)
            if measured is None:
                failing.append(qname)
                warnings.append(f"gold:{qname}:measured_missing")
                continue
            # Compute a single "representative" comparison. For list
            # quantities (eg. u_centerline as 17 floats), compare
            # elementwise and report the worst-case relative error.
            agg = self._aggregate_compare(qname, measured, ref_values, tolerance)
            if agg is None:
                continue
            if not agg.all_pass:
                failing.append(qname)
            results.append(agg)

        return ComparisonResult(
            all_pass=len(failing) == 0 and len(results) > 0,
            quantities=results,
            failing_quantities=failing,
            tolerance_warnings=warnings,
        )

    def _aggregate_compare(
        self,
        qname: str,
        measured: Any,
        ref_values: List[Dict[str, Any]],
        tolerance: float,
    ) -> Optional[QuantityResult]:
        """Compare a measured quantity against a list of reference points.

        For scalar quantities (eg. strouhal_number, nusselt_number),
        `ref_values` is a list with one entry and `measured` is a
        scalar.

        For vector quantities (eg. u_centerline), `ref_values` is a
        list of {y: ..., u: ...} dicts and `measured` is a list of
        floats (same length). We compare the L2-relative error.
        """
        # Scalar path
        if len(ref_values) == 1 and "value" in ref_values[0]:
            gold = float(ref_values[0]["value"])
            m = float(measured) if not isinstance(measured, list) else float(measured[0])
            if gold == 0:
                # Use absolute error when gold is zero.
                abs_err = abs(m - gold)
                rel_err = abs_err if abs_err < 1.0 else float("inf")
            else:
                rel_err = abs(m - gold) / abs(gold)
            return QuantityResult(
                name=qname,
                measured=m,
                gold=gold,
                relative_error=rel_err,
                tolerance=tolerance,
                all_pass=rel_err <= tolerance,
            )
        # Vector path: align measured list with the gold point count
        if isinstance(measured, list) and len(measured) == len(ref_values):
            errs: List[Tuple[float, float, float]] = []  # (measured, gold, rel_err)
            for m, ref in zip(measured, ref_values):
                # The gold point may carry the value under various
                # keys (u, v, T, etc.). Pick whichever is not the
                # coordinate.
                coord_keys = {k for k in ref if k in ("y", "x", "z", "r")}
                value_keys = set(ref) - coord_keys
                if not value_keys:
                    continue
                vkey = sorted(value_keys)[0]
                g = float(ref[vkey])
                mm = float(m)
                if g == 0:
                    rel_err = abs(mm - g) if abs(mm - g) < 1.0 else float("inf")
                else:
                    rel_err = abs(mm - g) / abs(g)
                errs.append((mm, g, rel_err))
            if not errs:
                return None
            # Worst-case relative error across the vector.
            worst_idx = max(range(len(errs)), key=lambda i: errs[i][2])
            m_w, g_w, r_w = errs[worst_idx]
            return QuantityResult(
                name=qname,
                measured=m_w,
                gold=g_w,
                relative_error=r_w,
                tolerance=tolerance,
                all_pass=r_w <= tolerance,
            )
        # Length mismatch — record as failing with a clear note.
        return QuantityResult(
            name=qname,
            measured=float("nan"),
            gold=float("nan"),
            relative_error=float("inf"),
            tolerance=tolerance,
            all_pass=False,
        )
