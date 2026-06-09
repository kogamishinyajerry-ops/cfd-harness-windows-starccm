"""Placeholder: the Codebuddy REPL bridge (Stage 3+)."""
from __future__ import annotations

from typing import Any, Dict

__all__ = ["CodebuddyRepl", "ReplResponse"]


class ReplResponse:
    """A response from the Codebuddy REPL (Stage 3+ placeholder)."""
    def __init__(self, success: bool, payload: Dict[str, Any], raw: str = "") -> None:
        self.success = success
        self.payload = payload
        self.raw = raw


class CodebuddyRepl:
    """Stage 3+ placeholder for the Codebuddy REPL wrapper.

    In Stage 3+, this class will:
      1. Launch `python D:\\StarCCM Codebuddy\\starccm_cli_repl.py`
         as a subprocess.
      2. Send commands over stdin (one JSON per line).
      3. Parse JSON responses from stdout.
      4. Handle session lifecycle (start, restart, kill).
    """
    def __init__(self, codebuddy_path: str = r"D:\StarCCM Codebuddy\starccm_cli_repl.py") -> None:
        self.codebuddy_path = codebuddy_path

    def send_command(self, command: str, args: Dict[str, Any]) -> ReplResponse:
        raise NotImplementedError(
            f"CodebuddyRepl.send_command is Stage 3+; "
            f"command={command!r} args={args}"
        )
