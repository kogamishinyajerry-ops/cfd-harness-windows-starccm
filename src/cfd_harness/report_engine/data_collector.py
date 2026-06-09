"""DataCollector: gather everything the report engine needs to render.

Solver-agnostic. Pulls:
  - the auto-verifier's VerifierReport
  - the run's RunReport (for executor_mode, contract_hash, etc.)
  - the gold standard's path + solver_info

Writes a single `reports/<case>/<timestamp>/data.json` that the
generator renders into a markdown report.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from cfd_harness.auto_verifier.schemas import VerifierReport
from cfd_harness.executor.base import RunReport
from cfd_harness.models import TaskSpec

__all__ = ["DataCollector"]


class DataCollector:
    """Collects V&V run data into a single JSON file."""
    def __init__(self, output_root: Path) -> None:
        self.output_root = output_root

    def collect(
        self,
        task_spec: TaskSpec,
        run_report: RunReport,
        verifier_report: VerifierReport,
    ) -> Path:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out_dir = self.output_root / task_spec.case_id / timestamp
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "data.json"
        payload: Dict[str, Any] = {
            "task_spec": {
                "case_id": task_spec.case_id,
                "flow_type": task_spec.flow_type.value,
                "geometry_type": task_spec.geometry_type.value,
                "parameters": dict(task_spec.parameters),
                "gold_anchor": task_spec.gold_anchor,
                "solver_profile": task_spec.solver_profile,
                "mesh_density": task_spec.mesh_density,
            },
            "run_report": {
                "mode": run_report.mode.value,
                "status": run_report.status.value,
                "contract_hash": run_report.contract_hash,
                "version": run_report.version,
                "notes": list(run_report.notes),
                "execution_result": (
                    {
                        "success": run_report.execution_result.success,
                        "is_mock": run_report.execution_result.is_mock,
                        "residuals": dict(run_report.execution_result.residuals),
                        "key_quantities": dict(run_report.execution_result.key_quantities),
                        "execution_time_s": run_report.execution_result.execution_time_s,
                    }
                    if run_report.execution_result is not None
                    else None
                ),
            },
            "verifier_report": verifier_report.to_dict(),
        }
        out_file.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return out_file
