"""starccm-bridge: subprocess wrapper for the user's Codebuddy REPL.

Plane: ADAPTER_STARCCM (separate sub-package to keep
``cfd_harness.starccm_adapter`` importable on a fresh venv without
the bridge).

The bridge calls ``D:\\StarCCM Codebuddy\\starccm_cli.py`` (the user's
existing CLI, v15+ as of 2026-06-09). We DO NOT re-implement the
CLI; we wrap it. The CLI accepts one command per subprocess call and
returns a uniform JSON schema::

    {ok, command, timestamp, version, data, error}

Public surface (re-exported here for ``from starccm_bridge import ...``):
  - CodebuddyRepl: subprocess wrapper
  - CodebuddyResponse: the typed response
  - CodebuddyError: raised on structured errors
"""
from starccm_bridge.repl import CodebuddyError, CodebuddyRepl, CodebuddyResponse

__all__ = ["CodebuddyRepl", "CodebuddyResponse", "CodebuddyError"]
