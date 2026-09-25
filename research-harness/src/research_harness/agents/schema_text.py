"""Instruction text that embeds each JSON schema.

The models emit JSON (with a few extra helper fields), so the instructions show
the exact schema and an annotated example. Pure functions, unit tested.
"""

from __future__ import annotations

import json
from typing import Optional

from research_harness.state import CodeResult, PresentationResult, ResearchPlan


def schema_block(model_cls) -> str:
    """Render a JSON schema for ``model_cls`` with helper fields preserved."""
    schema = model_cls.model_json_schema()
    # Keep the code-run helper field on the outer object.
    return json.dumps(schema, indent=2)


def _annotation(s, kind):
    return f"- `{s}` -> {kind}  (not validated, for humans)"


def _plan_schema(s: str) -> str:
    lines = [
        _annotation("topic", "str, never empty"),
        _annotation("folder_name", "slug, from slugify(topic)"),
        _annotation("branch_name", "slug, from git_branch_prefix + slugify(topic)"),
        _annotation("scope", "one of research, coding, production"),
        _annotation("hypothesis", "one-sentence ML/analysis thesis"),
        _annotation("success_criteria", "what tests prove it works"),
        _annotation("tech_stack", "list of {name, why} items"),
        _annotation("files", "list of {path, why} items"),
    ]
    return "\n".join(lines)


def _code_schema(s: str) -> str:
    return "\n".join(
        [
            _annotation("src_files", "list of {path, code}"),
            _annotation("test_files", "list of {path, code}"),
            _annotation("run_command", "str, e.g. 'uv run pytest'"),
            _annotation("observations", "str, what the run did/what's needed to review"),
        ]
    )


def _presentation_schema(s: str) -> str:
    return "\n".join(
        [
            _annotation("notes_markdown", "str, notes.md content"),
            _annotation("readme_markdown", "str, project README.md content"),
            _annotation("root_readme_section", "str, markdown to add to repo README"),
        ]
    )


def _wrapper(opening, schema, closing, topic: str) -> str:
    return (
        opening
        + schema
        + "\n\n"
        + closing
        + f"\n\nInvestigate this topic: \"{topic}\".\n"
    )


def plan_instructions(topic: str) -> str:
    """Instructions for the researcher: emit a :class:`ResearchPlan`."""
    schema = schema_block(ResearchPlan) + "\n\n" + _plan_schema(topic)
    return _wrapper(
        "You are the researcher. Read the repo's AGENTS.md for conventions and "
        "its top-level README to understand existing projects, then investigate "
        "the topic, then output JSON only:\n",
        schema,
        "Rules:\n"
        "- Output ONLY JSON, nothing else.\n"
        "- Follow the repo's conventions exactly (uv + tests + no heavy markdown bold).\n",
        topic,
    )


def code_instructions(topic: str) -> str:
    """Instructions for the coder: emit a :class:`CodeResult`."""
    schema = schema_block(CodeResult) + "\n\n" + _code_schema(topic)
    return _wrapper(
        "You are the coder. Read the researcher's plan JSON, implement it under the "
        "project's src/ and tests/ folders, then run the code. Output JSON only:\n",
        schema,
        "Rules:\n"
        "- Output ONLY JSON, nothing else.\n"
        "- Write the source, tests, pyproject.toml and README as the plan requires.\n"
        "- Quote the exact command you ran to verify it works.",
        topic,
    )


def report_instructions(topic: str) -> str:
    """Instructions for the reporter: emit a :class:`PresentationResult`."""
    schema = schema_block(PresentationResult) + "\n\n" + _presentation_schema(topic)
    return _wrapper(
        "You are the reporter. Read the code result JSON and write polished markdown "
        "for this topic's project. Output JSON only:\n",
        schema,
        "Rules:\n"
        "- Output ONLY JSON, nothing else.\n"
        "- Follow the repo's conventions (markdown: avoid heavy inline **bold**; "
        "use headings, tables and code fences).\n",
        topic,
    )
