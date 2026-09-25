"""Thin subprocess runner for the repo tooling (``uv``, ``pytest``, ``git``).

This is the single execution point for the harness. Command *planning* lives in
:mod:`research_harness.tools.repo` (splitting/validation); here we only execute
and capture output. Kept separate so the deterministic layer can be unit tested
without spawning processes.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Union


@dataclass
class ShellResult:
    """The result of a shell execution."""

    success: bool
    stdout: str
    stderr: str
    returncode: int
    command: str

    def __bool__(self) -> bool:  # truthy iff the command succeeded
        return self.success


def run_shell(line: str, cwd: Path = Path("."), args: Optional[List[str]] = None, check: bool = True) -> ShellResult:
    """Execute ``line`` in ``cwd`` and return a :class:`ShellResult`.

    If ``check`` is True and the command fails, the exception is re-raised so a
    failed ``pytest``/``uv`` run aborts the research process.
    """
    command = f"{line} {args[0]}" if (args and not line.endswith((" ", "\t"))) else line
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        return ShellResult(
            success=False,
            stdout="",
            stderr=f"command not found: {command}",
            returncode=127,
            command=command,
        )
    shell_result = ShellResult(
        success=result.returncode == 0,
        stdout=result.stdout or "",
        stderr=result.stderr or "",
        returncode=result.returncode,
        command=command,
    )
    if check and not shell_result.success:
        raise RuntimeError(f"command failed (exit {result.returncode}):\n{command}\n\n{result.stderr or result.stdout}")
    return shell_result
