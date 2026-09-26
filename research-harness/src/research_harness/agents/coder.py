"""Builds the coder (implementation) agent."""

from __future__ import annotations

from agno.agent import Agent

from research_harness.agents.factory import build_agent
from research_harness.agents.schema_text import code_instructions
from research_harness.agents.tools import bind_tools


def build_coder(model, project_path, topic=None, tools=None) -> Agent:
    """Create the coder agent that writes code + tests and runs them.

    ``tools`` overrides the default tool set (bound to ``project_path``).
    """
    if tools is None:
        tools = bind_tools(project_path)
    return build_agent(
        name="coder",
        model=model,
        instructions=code_instructions(topic or ""),
        tools=tools,
    )
