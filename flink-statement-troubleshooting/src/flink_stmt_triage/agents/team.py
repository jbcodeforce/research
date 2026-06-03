"""Agno Team for Flink statement triage (optional LLM synthesis)."""

from __future__ import annotations

import os
from typing import Any

from flink_stmt_triage.config import TriageConfig, load_dotenv_file
from flink_stmt_triage.tools import (
    check_statement_health,
    detect_statement_issues,
    get_statement_exceptions,
    get_statement_profile,
    get_statement_status,
    query_pool_cfu,
    query_statement_metrics,
)


def _make_model():
    """Return an OpenAI-compatible model from environment."""
    from agno.models.openai import OpenAIChat

    load_dotenv_file()
    base_url = os.getenv("LLM_URL", "http://127.0.0.1:11434/v1")
    model_id = os.getenv("LLM_MODEL", "qwen2.5:latest")
    api_key = os.getenv("OPENAI_API_KEY", "ollama")
    return OpenAIChat(id=model_id, base_url=base_url, api_key=api_key)


def build_triage_team(config: TriageConfig | None = None):
    """Create Agno Team with statement, metrics, and profiler sub-agents."""
    from agno.agent import Agent
    from agno.team.mode import TeamMode
    from agno.team.team import Team

    cfg = config

    def status_tool(statement_name: str) -> str:
        return str(get_statement_status(statement_name, cfg))

    def exceptions_tool(statement_name: str) -> str:
        return str(get_statement_exceptions(statement_name, cfg))

    def health_tool(statement_name: str) -> str:
        return str(check_statement_health(statement_name, cfg))

    def metrics_tool(statement_name: str, compute_pool_id: str, window_minutes: int = 30) -> str:
        return str(query_statement_metrics(statement_name, compute_pool_id, window_minutes, cfg))

    def cfu_tool(compute_pool_id: str, window_minutes: int = 30) -> str:
        return str(query_pool_cfu(compute_pool_id, window_minutes, cfg))

    def issues_tool(statement_name: str, compute_pool_id: str, window_minutes: int = 30) -> str:
        return str(detect_statement_issues(statement_name, compute_pool_id, window_minutes, cfg))

    def profile_tool(statement_name: str, compute_pool_id: str) -> str:
        return str(get_statement_profile(statement_name, compute_pool_id, cfg))

    status_agent = Agent(
        name="StatementStatusAgent",
        role="Inspect Flink statement phase, detail, and exceptions",
        tools=[status_tool, exceptions_tool, health_tool],
        instructions=[
            "Use tools to report statement phase, health, and any exceptions.",
            "Return concise factual findings only.",
        ],
    )

    metrics_agent = Agent(
        name="MetricsAgent",
        role="Query Flink statement and pool metrics",
        tools=[metrics_tool, cfu_tool],
        instructions=[
            "Query statement metrics and compute pool CFU.",
            "Summarize num_records_in, num_records_out, pending_records, state size.",
        ],
    )

    profiler_agent = Agent(
        name="ProfilerAgent",
        role="Detect issues and profile bottlenecks",
        tools=[issues_tool, profile_tool],
        instructions=[
            "Run issue detection and note profiler limitations.",
            "Highlight backpressure, zero-input, and zero-output patterns.",
        ],
    )

    return Team(
        name="FlinkTriageTeam",
        mode=TeamMode.coordinate,
        model=_make_model(),
        members=[status_agent, metrics_agent, profiler_agent],
        instructions=[
            "You lead Flink SQL statement troubleshooting for Confluent Cloud.",
            "Delegate to StatementStatusAgent for phase and exceptions.",
            "Delegate to MetricsAgent for throughput and CFU metrics.",
            "Delegate to ProfilerAgent for issue detection.",
            "Synthesize a markdown report with: Summary, Evidence, Metrics, Hypotheses, Actions.",
        ],
        markdown=True,
    )


def run_agno_triage(
    statement_name: str,
    compute_pool_id: str,
    window_minutes: int = 30,
    config: TriageConfig | None = None,
) -> Any:
    """Run Agno team and return response object."""
    team = build_triage_team(config)
    prompt = (
        f"Triage Flink statement `{statement_name}` on compute pool `{compute_pool_id}`. "
        f"Use a {window_minutes} minute metrics window."
    )
    return team.run(prompt)
