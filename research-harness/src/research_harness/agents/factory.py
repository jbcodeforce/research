"""Model + agent factory: builds Agno agents from config.

Holds the canonical system prompts / instructions for each role so the same
knowledge is reused by both the real workflow (LLM) and any test doubles.
"""

from __future__ import annotations

import os
from typing import List, Optional

from agno.agent import Agent
from agno.models.base import Model
from agno.models.openai.chat import OpenAIChat

from research_harness.config import HarnessConfig

CONVENTIONS = """You must follow this repository's workflow conventions exactly:
- Python with `uv`; `src/<package>/` layout, `tests/`, `pyproject.toml` (hatchling),
  console scripts under `[project.scripts]`, pytest with `testpaths = ["tests"]`.
- Test-driven development: write unit tests in `tests/` BEFORE production code.
- Share logic in common utilities; do not duplicate functions.
- Markdown: avoid heavy inline **bold**; use headings, tables and code fences."""


def build_model(config: HarnessConfig, stub_response: Optional[str] = None, stub_responses: Optional[List[str]] = None) -> Model:
    """Build the LLM model for an agent.

    If ``stub_responses`` (a list) is given, a :class:`SequenceModel` is returned
    that pops a canned response per LLM call, so the whole workflow runs offline
    with per-step control (used by tests). Otherwise a real
    OpenAI-compatible :class:`OpenAIChat` model is returned.
    """
    from research_harness.tools.stub import SequenceModel, StubModel

    if stub_responses:
        return SequenceModel(responses=stub_responses)
    if stub_response is not None:
        return StubModel(response=stub_response)

    return OpenAIChat(
        id=config.llm.model_id,
        base_url=config.llm.base_url,
        api_key=config.llm.api_key or os.getenv("OPENAI_API_KEY"),
        temperature=config.llm.temperature,
        max_tokens=config.llm.max_tokens,
    )


def build_agent(
    name: str,
    model: Model,
    instructions: str,
    input_schema: object = None,
    markdown: bool = True,
    tools=None,
) -> Agent:
    """Create an :class:`Agent` bound to ``model`` with a single block of instructions."""
    return Agent(
        name=name,
        model=model,
        instructions=instructions,
        input_schema=input_schema,
        markdown=markdown,
        tools=tools,
    )
