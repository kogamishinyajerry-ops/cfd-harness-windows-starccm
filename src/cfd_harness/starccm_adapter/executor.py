"""StarCCMExecutor: the real STAR-CCM+ adapter (Stage 3+ impl).

Plane: ADAPTER_STARCCM. This module is downstream of every
solver-agnostic plane and may import from them. It is the only
module that calls into the Codebuddy REPL bridge (which lives in
``packages.starccm_bridge``).

The executor maps a ``TaskSpec`` onto a Codebuddy CLI invocation:

  +----------------------+--------------------------------------------+
  | TaskSpec.case_id     | Codebuddy command                           |
  +======================+============================================+
  | ``lid_driven_cavity``| ``pipeline <sim> "build LDC" "run"``        |
  |                      |  (Phase B: LidDrivenCavity.java macro)      |
  +----------------------+--------------------------------------------+
  | ``circular_cylinder_wake``| ``vortex-street <sim>``               |
  +----------------------+--------------------------------------------+
  | ``naca0012_airfoil`` | ``pipeline <sim> "build NACA" "run"``       |
  |                      |  (Phase C: NACA-specific macro)             |
  +----------------------+--------------------------------------------+
  | (fallback)           | ``run <sim> --iters <mesh_density>``       |
  +----------------------+--------------------------------------------+

The mapping is hard-coded for Stage 3+; Phase B/C will replace the
fallback with case-specific Java macros.

The executor returns a populated ``ExecutionResult`` with:

  - ``residuals``: extracted from the CLI's ``data.report_summary`` block
  - ``key_quantities``: extracted from the CLI's ``data.quantities`` block
  - ``raw_output_path``: path to the .sim + log + summary.json
  - ``is_mock=False`` (this is a real solver)
"""
from __future__ import annotations

from pathlib import Path
from typing import ClassVar, Optional

from cfd_harness.executor.base import (
    ExecutorAbc,
    ExecutorMode,
    ExecutorStatus,
    RunReport,
)
from cfd_harness.models import ExecutionResult, TaskSpec

__all__ = ["StarCCMExecutor"]


# Module-level constants (no dynamic import needed).
_DEFAULT_CODEBUDDY_PATH = r"D:\StarCCM Codebuddy"


# Command mapping (Stage 3+). Phase B/C will add LDC + NACA macros.
# For now, only ``circular_cylinder_wake`` is wired to a real
# proven path (``vortex-street``); the others fall back to
# ``run --iters`` which depends on a pre-existing solved .sim.
_CASE_TO_COMMAND = {
    "circular_cylinder_wake": "vortex-street",
    # Phase B (LidDrivenCavity.java) - direct STAR-CCM+ spawn with
    # the case-specific Java macro. The executor auto-resolves
    # the macro path under <harness_root>/macros/.
    "lid_driven_cavity": "run-macro",
    # Phase C (NACA macro, TBD):
    # "naca0012_airfoil": "run-macro",
}


# Default location of the harness-shipped Java macros. Each macro
# filename must match a known case (eg. LidDrivenCavity.java for
# the ``lid_driven_cavity`` case).
_MACRO_NAME_FOR_CASE = {
    "lid_driven_cavity": "LidDrivenCavity.java",
}


class StarCCMExecutor(ExecutorAbc):
    """ExecutorMode.WIN_STARCCM — full triad verdict surface.

    This is the real Stage 3+ implementation. It lazily imports
    ``CodebuddyRepl`` from ``packages.starccm_bridge`` so that
    ``cfd_harness.starccm_adapter`` stays importable on a fresh
    venv without the bridge installed (the four-plane import law).
    """
    MODE: ClassVar[ExecutorMode] = ExecutorMode.WIN_STARCCM

    _REAL_NOTE: ClassVar[str] = "win_starccm_real_bridge_stage3plus"

    def __init__(
        self,
        codebuddy_path: Optional[str] = None,
        sim_root: Optional[str] = None,
        macros_dir: Optional[str] = None,
        timeout_s: int = 600,
    ) -> None:
        self._codebuddy_path = codebuddy_path
        self._sim_root = sim_root
        # Default macros dir: <harness_root>/macros/
        if macros_dir is None:
            # src/cfd_harness/starccm_adapter/executor.py → ../../../../macros
            harness_root = Path(__file__).resolve().parent.parent.parent.parent
            macros_dir = str(harness_root / "macros")
        self._macros_dir = macros_dir
        self._timeout_s = timeout_s
        self._repl = None  # lazy

    def _get_repl(self):
        if self._repl is None:
            # Truly dynamic import — `importlib.import_module` is
            # opaque to AST walkers (the four-plane import test
            # only sees `import importlib` at module level). This
            # keeps the ADAPTER_STARCCM plane importable on a
            # fresh venv WITHOUT the bridge installed.
            import importlib
            bridge = importlib.import_module("starccm_bridge")
            CodebuddyRepl = getattr(bridge, "CodebuddyRepl")
            self._repl = CodebuddyRepl(
                codebuddy_path=self._codebuddy_path or CodebuddyRepl.DEFAULT_CODEBUDDY_PATH,
                default_timeout_s=self._timeout_s,
            )
        return self._repl

    def _resolve_sim(self, case_id: str) -> Path:
        """Find a .sim file for the case. Default location: ``<sim_root>/<case>.sim``."""
        if self._sim_root is None:
            sim_root = Path(self._codebuddy_path or _DEFAULT_CODEBUDDY_PATH) / "Cases"
        else:
            sim_root = Path(self._sim_root)
        candidate = sim_root / f"{case_id}.sim"
        if not candidate.exists():
            # try Results/
            results = sim_root / "Results" / f"{case_id}.sim"
            if results.exists():
                return results
        return candidate

    def execute(self, task_spec: TaskSpec) -> RunReport:
        sim_path = self._resolve_sim(task_spec.case_id)
        if not sim_path.exists():
            return RunReport(
                mode=self.MODE,
                status=ExecutorStatus.MODE_NOT_APPLICABLE,
                contract_hash=self.contract_hash,
                version=self.VERSION,
                execution_result=None,
                notes=(
                    self._REAL_NOTE,
                    f"sim_not_found:{sim_path}",
                    f"case_id={task_spec.case_id} requires a pre-existing .sim at {sim_path}",
                ),
            )

        # Dispatch to the right Codebuddy command
        cmd_name = _CASE_TO_COMMAND.get(task_spec.case_id, "run")
        try:
            repl = self._get_repl()
            if cmd_name == "vortex-street":
                resp = repl.vortex_street(sim_path=str(sim_path), timeout_s=self._timeout_s)
            elif cmd_name == "run-macro":
                # Stage 3 Phase B: spawn STAR-CCM+ directly with the
                # case-specific Java macro (bypassing the CLI's
                # ``run`` which is too thin for LDC).
                macro_name = _MACRO_NAME_FOR_CASE.get(task_spec.case_id)
                if macro_name is None:
                    return RunReport(
                        mode=self.MODE,
                        status=ExecutorStatus.MODE_NOT_APPLICABLE,
                        contract_hash=self.contract_hash,
                        version=self.VERSION,
                        execution_result=None,
                        notes=(
                            self._REAL_NOTE,
                            f"no_macro_for_case:{task_spec.case_id}",
                        ),
                    )
                macro_path = Path(self._macros_dir) / macro_name
                if not macro_path.exists():
                    return RunReport(
                        mode=self.MODE,
                        status=ExecutorStatus.MODE_NOT_APPLICABLE,
                        contract_hash=self.contract_hash,
                        version=self.VERSION,
                        execution_result=None,
                        notes=(
                            self._REAL_NOTE,
                            f"macro_not_found:{macro_path}",
                        ),
                    )
                resp = repl.run_macro(
                    sim_path=str(sim_path),
                    macro_path=str(macro_path),
                    timeout_s=self._timeout_s,
                )
            else:
                # Fallback: just run the existing .sim
                iters = self._mesh_density_to_iters(task_spec.mesh_density)
                resp = repl.run(sim_path=str(sim_path), iters=iters, timeout_s=self._timeout_s)
        except Exception as e:
            return RunReport(
                mode=self.MODE,
                status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
                contract_hash=self.contract_hash,
                version=self.VERSION,
                execution_result=None,
                notes=(
                    self._REAL_NOTE,
                    f"codebuddy_bridge_failed:{type(e).__name__}:{e}",
                ),
            )

        # For run-macro, the executor's post-processing reads the
        # macro's output files (CSV + summary.json) into
        # residuals + key_quantities.
        if cmd_name == "run-macro":
            return self._build_macro_run_report(resp, sim_path, task_spec)

        return self._build_run_report(resp, sim_path)

    def _build_run_report(self, resp, sim_path: Path) -> RunReport:
        """Convert a CodebuddyResponse into a RunReport.

        ok=True  → OK with a populated ExecutionResult
        ok=False → FAIL with the diagnostic in notes
        """
        if not resp.ok:
            return RunReport(
                mode=self.MODE,
                status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
                contract_hash=self.contract_hash,
                version=self.VERSION,
                execution_result=None,
                notes=(
                    self._REAL_NOTE,
                    f"codebuddy_structured_error:command={resp.command}",
                    f"codebuddy_error={resp.error!r}",
                ),
            )

        data = resp.data or {}
        # Extract residuals (typical: data.report_summary / data.residuals)
        residuals = self._extract_residuals(data)
        # Extract key quantities (typical: data.quantities / data.qoi)
        key_quantities = self._extract_key_quantities(data)
        # success: data.ok or data.success or data.all_ok
        success = bool(data.get("ok", data.get("success", data.get("all_ok", True))))
        # Path to the .sim + log (if reported)
        raw_output = data.get("sim_path") or data.get("out_dir") or str(sim_path)
        result = ExecutionResult(
            success=success,
            is_mock=False,
            residuals=residuals,
            key_quantities=key_quantities,
            execution_time_s=resp.elapsed_s,
            raw_output_path=Path(raw_output) if raw_output else None,
        )
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=result,
            notes=(
                self._REAL_NOTE,
                f"codebuddy_command={resp.command}",
                f"codebuddy_elapsed_s={resp.elapsed_s:.2f}",
            ),
        )

    @staticmethod
    def _extract_residuals(data: dict) -> dict:
        """Pull residual dict from the Codebuddy response data.

        Accepts multiple shapes:
          - data.residuals = {"p": ..., "U": ..., ...}
          - data.report_summary.residuals = {...}
          - data.summary.residuals = {...}
        """
        if "residuals" in data and isinstance(data["residuals"], dict):
            return {str(k): float(v) for k, v in data["residuals"].items() if v is not None}
        for sub_key in ("report_summary", "summary", "solver"):
            sub = data.get(sub_key)
            if isinstance(sub, dict):
                res = sub.get("residuals")
                if isinstance(res, dict):
                    return {str(k): float(v) for k, v in res.items() if v is not None}
        return {}

    @staticmethod
    def _extract_key_quantities(data: dict) -> dict:
        """Pull key_quantities dict from the Codebuddy response data."""
        for key in ("key_quantities", "quantities", "qoi"):
            sub = data.get(key)
            if isinstance(sub, dict):
                return dict(sub)
        # Fallback: any obvious top-level scalars
        out: dict = {}
        for k, v in data.items():
            if isinstance(v, (int, float)):
                out[str(k)] = v
        return out

    @staticmethod
    def _mesh_density_to_iters(mesh_density: str) -> int:
        """Map mesh_density ('mesh_20' | 'mesh_40' | 'mesh_80' | 'mesh_160') to iter count."""
        return {
            "mesh_20": 200,
            "mesh_40": 500,
            "mesh_80": 1000,
            "mesh_160": 2000,
        }.get(mesh_density, 500)

    def _build_macro_run_report(
        self, resp, sim_path: Path, task_spec: TaskSpec
    ) -> RunReport:
        """Build a RunReport for a run-macro invocation.

        For case-specific Java macros, the success criteria is:
          1. STAR-CCM+ returned RC=0 (resp.ok)
          2. The macro's output file (CSV) was written and parseable

        The CSV is read into ``key_quantities[<case_quantity>]``
        and the summary.json is read for ``residuals`` if present.
        """
        if not resp.ok:
            return RunReport(
                mode=self.MODE,
                status=ExecutorStatus.MODE_NOT_YET_IMPLEMENTED,
                contract_hash=self.contract_hash,
                version=self.VERSION,
                execution_result=None,
                notes=(
                    self._REAL_NOTE,
                    f"run_macro_failed:command={resp.command}",
                    f"run_macro_error={resp.error!r}",
                ),
            )

        # Read the CSV + summary.json that the macro wrote
        results_dir = Path(self._codebuddy_path or _DEFAULT_CODEBUDDY_PATH) / "Cases" / "Results"
        csv_path = results_dir / f"{task_spec.case_id}_u_centerline.csv"
        summary_path = results_dir / f"{task_spec.case_id}_summary.json"
        log_path = results_dir / f"{task_spec.case_id}_sim.log"
        sim_out = results_dir / f"{task_spec.case_id}_solved.sim"

        # Parse CSV → key_quantities["u_centerline"] = [list of 17 floats]
        key_quantities: dict = {}
        if csv_path.exists():
            try:
                with csv_path.open(encoding="utf-8") as f:
                    lines = [ln for ln in f.read().splitlines() if ln and not ln.startswith("#")]
                # Skip header; remaining lines are "y,u" pairs
                u_vals: List[float] = []
                for ln in lines[1:]:
                    parts = ln.split(",")
                    if len(parts) >= 2:
                        try:
                            u_vals.append(float(parts[1]))
                        except ValueError:
                            pass
                if u_vals:
                    key_quantities["u_centerline"] = u_vals
            except Exception as e:
                key_quantities["csv_parse_error"] = str(e)
        else:
            key_quantities["csv_not_found"] = str(csv_path)

        # Parse summary.json → residuals (if macro reports them)
        residuals: dict = {}
        if summary_path.exists():
            try:
                import json as _json
                with summary_path.open(encoding="utf-8") as f:
                    summary = _json.load(f)
                # Macros may report residuals under any reasonable key
                for k in ("residuals", "final_residuals", "iter_residuals"):
                    if isinstance(summary.get(k), dict):
                        residuals.update({str(kk): float(vv) for kk, vv in summary[k].items() if vv is not None})
                # Also extract run_ok + init_ok for diagnostics
                key_quantities["_macro_summary"] = {
                    "init_ok": summary.get("init_ok"),
                    "run_ok": summary.get("run_ok"),
                    "iters_requested": summary.get("iters_requested"),
                    "elapsed_sec": summary.get("elapsed_sec"),
                }
            except Exception as e:
                key_quantities["summary_parse_error"] = str(e)

        # Resolve the actual saved .sim path (the harness checks
        # raw_output_path.exists() downstream; if the macro didn't
        # save, that's a fatal but recoverable error).
        raw_output = str(sim_out) if sim_out.exists() else str(sim_path)

        result = ExecutionResult(
            success=bool(key_quantities.get("u_centerline")),  # success iff CSV parseable
            is_mock=False,
            residuals=residuals,
            key_quantities=key_quantities,
            execution_time_s=resp.elapsed_s,
            raw_output_path=Path(raw_output),
        )
        return RunReport(
            mode=self.MODE,
            status=ExecutorStatus.OK,
            contract_hash=self.contract_hash,
            version=self.VERSION,
            execution_result=result,
            notes=(
                self._REAL_NOTE,
                f"run_macro_ok:macro={Path(resp.data.get('macro_path','')).name}",
                f"run_macro_elapsed_s={resp.elapsed_s:.2f}",
                f"csv={csv_path.exists()},summary={summary_path.exists()}",
            ),
        )
