"""Agent-agnostic tool functions for Flink statement triage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from flink_stmt_triage.config import TriageConfig, get_config, try_get_config
from flink_stmt_triage.flink_queries import (
    all_statement_metrics_queries,
    pool_cfu_query,
)
from flink_stmt_triage.flink_rest import FlinkRestClient, statement_detail, statement_phase
from flink_stmt_triage.metrics_client import MetricsClient, query_metrics
from flink_stmt_triage.report import build_triage_report

_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    path = _FIXTURES / name
    return json.loads(path.read_text())


def get_statement_status(statement_name: str, config: TriageConfig | None = None) -> dict[str, Any]:
    """Return statement JSON from Flink REST."""
    cfg = config or get_config()
    client = FlinkRestClient(cfg)
    stmt = client.get_statement(statement_name)
    return {
        "name": statement_name,
        "phase": statement_phase(stmt),
        "detail": statement_detail(stmt),
        "raw": stmt,
    }


def get_statement_exceptions(
    statement_name: str, config: TriageConfig | None = None
) -> dict[str, Any]:
    """Return recent exceptions for a statement."""
    cfg = config or get_config()
    return FlinkRestClient(cfg).get_exceptions(statement_name)


def check_statement_health(
    statement_name: str, config: TriageConfig | None = None
) -> dict[str, Any]:
    """Aggregate health check from status and phase."""
    status = get_statement_status(statement_name, config)
    phase = status["phase"]
    healthy = phase in ("RUNNING", "COMPLETED")
    return {
        "statement_name": statement_name,
        "phase": phase,
        "healthy": healthy,
        "detail": status.get("detail", ""),
    }


def query_statement_metrics(
    statement_name: str,
    compute_pool_id: str,
    window_minutes: int = 30,
    config: TriageConfig | None = None,
) -> dict[str, Any]:
    """Query all standard Flink statement metrics."""
    cfg = config or get_config()
    client = MetricsClient(cfg)
    queries = all_statement_metrics_queries(statement_name, compute_pool_id, window_minutes)
    return {name: client.query(payload) for name, payload in queries.items()}


def query_pool_cfu(
    compute_pool_id: str,
    window_minutes: int = 30,
    config: TriageConfig | None = None,
) -> dict[str, Any]:
    """Query current CFUs for a compute pool."""
    cfg = config or get_config()
    return query_metrics(cfg, pool_cfu_query(compute_pool_id, window_minutes))


def detect_statement_issues(
    statement_name: str,
    compute_pool_id: str,
    window_minutes: int = 30,
    config: TriageConfig | None = None,
) -> dict[str, Any]:
    """Rule-based issue detection from status and metrics."""
    status = get_statement_status(statement_name, config)
    metrics = query_statement_metrics(
        statement_name, compute_pool_id, window_minutes, config
    )
    from flink_stmt_triage.metrics_client import latest_value
    from flink_stmt_triage.report import summarize_metric

    issues: list[str] = []
    phase = status["phase"]
    if phase == "FAILED":
        issues.append("Statement phase is FAILED")
    if phase == "PENDING":
        issues.append("Statement stuck in PENDING — check compute pool capacity")

    pending = latest_value(metrics.get("pending_records", {}))
    if pending and pending > 0:
        issues.append(f"Backpressure: pending_records={pending}")

    rec_in = latest_value(metrics.get("num_records_in", {}))
    rec_out = latest_value(metrics.get("num_records_out", {}))
    if phase == "RUNNING" and rec_in == 0:
        issues.append("No input records — verify source topic and consumer offsets")
    if rec_in and rec_in > 0 and (rec_out or 0) == 0:
        issues.append("Input without output — check sink configuration")

    return {
        "statement_name": statement_name,
        "phase": phase,
        "issues": issues,
        "metrics_summary": {
            name: summarize_metric(name, resp).model_dump()
            for name, resp in metrics.items()
        },
    }


def get_statement_profile(
    statement_name: str,
    compute_pool_id: str,
    config: TriageConfig | None = None,
) -> dict[str, Any]:
    """Profiler placeholder — full task graph requires Confluent MCP or Console."""
    issues = detect_statement_issues(statement_name, compute_pool_id, config=config)
    return {
        "statement_name": statement_name,
        "note": (
            "Task-level Query Profiler data is available via Confluent MCP "
            "`get-flink-statement-profile` or the Cloud Console. "
            "This tool returns rule-based analysis from REST + metrics."
        ),
        "detected_issues": issues["issues"],
    }


def run_triage(
    statement_name: str,
    compute_pool_id: str,
    window_minutes: int = 30,
    config: TriageConfig | None = None,
) -> dict[str, Any]:
    """Full triage: collect evidence and return TriageReport as dict."""
    cfg = config or get_config()
    client = FlinkRestClient(cfg)
    stmt = client.get_statement(statement_name)
    exc = client.get_exceptions(statement_name)
    metrics = query_statement_metrics(statement_name, compute_pool_id, window_minutes, cfg)
    pool = query_pool_cfu(compute_pool_id, window_minutes, cfg)
    report = build_triage_report(
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        statement=stmt,
        exceptions=exc,
        metric_responses=metrics,
        pool_cfu=pool,
    )
    return report.model_dump()


def run_triage_dry_run(
    statement_name: str = "perf-dml-passthrough",
    compute_pool_id: str = "lfcp-example",
) -> dict[str, Any]:
    """Build report from fixture files (no live API)."""
    stmt = load_fixture("statement_running.json")
    exc = load_fixture("exceptions_empty.json")
    metrics = {
        "num_records_in": load_fixture("metric_records_in.json"),
        "num_records_out": load_fixture("metric_records_out.json"),
        "pending_records": load_fixture("metric_pending.json"),
        "statement_status": load_fixture("metric_status.json"),
        "state_size_bytes": load_fixture("metric_state_size.json"),
    }
    pool = load_fixture("metric_pool_cfu.json")
    report = build_triage_report(
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        statement=stmt,
        exceptions=exc,
        metric_responses=metrics,
        pool_cfu=pool,
    )
    return report.model_dump()


# Tool registry for schema export
TOOL_REGISTRY: dict[str, Any] = {
    "get_statement_status": get_statement_status,
    "get_statement_exceptions": get_statement_exceptions,
    "check_statement_health": check_statement_health,
    "query_statement_metrics": query_statement_metrics,
    "query_pool_cfu": query_pool_cfu,
    "detect_statement_issues": detect_statement_issues,
    "get_statement_profile": get_statement_profile,
    "run_triage": run_triage,
}
