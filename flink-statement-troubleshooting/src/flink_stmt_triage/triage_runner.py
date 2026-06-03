"""Deterministic triage orchestration (no LLM required)."""

from __future__ import annotations

from flink_stmt_triage.config import TriageConfig
from flink_stmt_triage.report import TriageReport
from flink_stmt_triage.tools import run_triage, run_triage_dry_run


def execute_triage(
    statement_name: str,
    compute_pool_id: str,
    *,
    window_minutes: int = 30,
    dry_run: bool = False,
    config: TriageConfig | None = None,
) -> TriageReport:
    """Run full triage pipeline and return structured report."""
    if dry_run:
        data = run_triage_dry_run(statement_name, compute_pool_id)
    else:
        data = run_triage(statement_name, compute_pool_id, window_minutes, config)
    return TriageReport.model_validate(data)
