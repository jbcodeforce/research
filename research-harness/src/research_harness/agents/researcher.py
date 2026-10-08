"""Builds the researcher (plan) agent."""

from __future__ import annotations

from agno.agent import Agent

from research_harness.agents.factory import build_agent
from research_harness.agents.tools import bind_tools

from research_harness.state import  ResearchPlan


def _wrapper(opening, schema, closing, topic: str) -> str:
    return (
        opening
        + schema
        + "\n\n"
        + closing
        + f"\n\nInvestigate this topic: \"{topic}\".\n"
    )

def _plan_instructions(topic: str) -> str:
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


def build_researcher(model, project_path, topic=None, tools=None) -> Agent:
    """Create the researcher agent that reads context and produces the plan.

    ``tools`` overrides the default read-only tool set (bound to ``project_path``).
    """
    if tools is None:
        tools = bind_tools(project_path)
    return build_agent(
        name="researcher",
        model=model,
        instructions=_plan_instructions(topic or ""),
        tools=tools,
    )
