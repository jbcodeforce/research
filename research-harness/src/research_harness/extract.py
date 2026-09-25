"""Robust extraction of JSON objects from free-form LLM text.

Agents return JSON as instructed, but real models may wrap it in prose or code
fences. These helpers find the JSON, then validate/parse it into a pydantic
model. Every function is pure and unit tested.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, TypeAdapter


def find_json(text: Any) -> Optional[dict]:
    """Extract the first JSON object from ``text``.

    Handles plain JSON, `````json fenced blocks, and leading/trailing prose.
    Returns ``None`` if no JSON object can be found.
    """
    if text is None:
        return None
    if isinstance(text, BaseModel):
        return text.model_dump()
    if isinstance(text, dict):
        return text
    if not isinstance(text, str):
        text = str(text)

    stripped = text.strip()
    if not stripped:
        return None

    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass

    # Try a ```json ... ``` fenced block.
    fenced = re.search(r"```(?:json|JSON)?\s*\n?(.*?)```", stripped, re.DOTALL)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except (json.JSONDecodeError, ValueError):
            pass

    # Try the first balanced `{...}` object (best-effort, brace-matching).
    start = stripped.find("{")
    if start != -1:
        depth = 0
        in_str = False
        escape = False
        for i in range(start, len(stripped)):
            ch = stripped[i]
            if in_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    fragment = stripped[start : i + 1]
                    try:
                        return json.loads(fragment)
                    except (json.JSONDecodeError, ValueError):
                        return None
    return None


def model_from_json(base_model: type[BaseModel], text: Any) -> Optional[BaseModel]:
    """Parse ``text`` into ``base_model`` or return ``None`` on failure.

    base_model
        The target schema.

    text
        Raw agent output, typically containing a JSON blob.

    Returns
    -------
    The validated model, or ``None`` if the text has no JSON or the data does not
    satisfy the schema.

    """
    data = find_json(text)
    if data is None:
        return None
    adapter = TypeAdapter(base_model)
    try:
        return adapter.validate_python(data)
    except Exception:
        return None
