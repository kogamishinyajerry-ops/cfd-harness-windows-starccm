"""Schemas: TypedDict / dataclass shapes used by the report engine."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

__all__ = ["ReportRequest"]


@dataclass(frozen=True)
class ReportRequest:
    """A request to render a report."""
    case_id: str
    data_path: str          # path to the data.json from DataCollector
    output_path: str        # path to write the markdown report
    template: Optional[str] = None  # optional template override (Stage 3+)
