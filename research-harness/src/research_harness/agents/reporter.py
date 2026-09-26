"""Builds the reporter (presentation) agent."""

from __future__ import annotations

from agno.agent import Agent

from research_harness.agents.factory import build_agent
from research_harness.agents.schema_text import report_instructions
from research_harness.agents.tools import bind_tools


def build_reporter(model, project_path, topic=None, tools=None) -> Agent:
    """Create the reporter agent that writes notes + README markdown.

    ``tools`` overrides the default tool set (bound to ``project_path``).
    """
    if tools is None:
        tools = bind_tools(project_path)
    return build_agent(
        name="reporter",
        model=model,
        instructions=report_instructions(topic or ""),
        tools=tools,
    )
