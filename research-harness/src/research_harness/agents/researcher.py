"""Builds the researcher (plan) agent."""

from __future__ import annotations

from agno.agent import Agent

from research_harness.agents.factory import build_agent
from research_harness.agents.schema_text import plan_instructions
from research_harness.agents.tools import bind_tools


def build_researcher(model, project_path, topic=None, tools=None) -> Agent:
    """Create the researcher agent that reads context and produces the plan.

    ``tools`` overrides the default read-only tool set (bound to ``project_path``).
    """
    if tools is None:
        tools = bind_tools(project_path)
    return build_agent(
        name="researcher",
        model=model,
        instructions=plan_instructions(topic or ""),
        tools=tools,
    )
