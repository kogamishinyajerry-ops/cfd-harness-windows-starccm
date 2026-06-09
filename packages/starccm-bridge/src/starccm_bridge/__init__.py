"""starccm-bridge: subprocess wrapper for the user's Codebuddy REPL.

Plane: ADAPTER_STARCCM (separate sub-package to keep the
`cfd_harness.starccm_adapter` package importable on a fresh venv
without the bridge).

The bridge calls `D:\\StarCCM Codebuddy\\starccm_cli_repl.py` (a
script the user has at v34, 1686 tests). We DO NOT re-implement the
CLI; we wrap it. The Repl accepts commands over stdin and returns
JSON over stdout — we send a command like `mesh_pipeline
--input <case.json> --output <out_dir>` and parse the response.
"""
# Stage 3+ re-exports (currently the module is a stub):
# from starccm_bridge.repl import CodebuddyRepl, ReplResponse
# from starccm_bridge.session import Session
# from starccm_bridge.error_parser import parse_error

__all__: list = []
