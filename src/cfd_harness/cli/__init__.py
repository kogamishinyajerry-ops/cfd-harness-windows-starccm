"""CLI subpackage for cfd-harness-windows-starccm.

Entry point: `python -m cfd_harness.cli.run` (the actual CLI lives in
`run.py`).
"""
from cfd_harness.cli.run import main, build_parser, ANCHOR_CASES

__all__ = ["main", "build_parser", "ANCHOR_CASES"]
