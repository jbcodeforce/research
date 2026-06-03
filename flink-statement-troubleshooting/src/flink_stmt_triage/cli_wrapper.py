"""Thin subprocess wrapper for confluent CLI (read-only)."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Any


def _confluent_bin() -> str:
    path = shutil.which("confluent")
    if not path:
        raise RuntimeError("confluent CLI not found in PATH")
    return path


def describe_statement(statement_name: str, output_format: str = "json") -> dict[str, Any]:
    """Run `confluent flink statement describe` and parse JSON output."""
    cmd = [
        _confluent_bin(),
        "flink",
        "statement",
        "describe",
        statement_name,
        "-o",
        output_format,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)


def list_statements(output_format: str = "json") -> dict[str, Any]:
    """Run `confluent flink statement list`."""
    cmd = [_confluent_bin(), "flink", "statement", "list", "-o", output_format]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return json.loads(result.stdout)
