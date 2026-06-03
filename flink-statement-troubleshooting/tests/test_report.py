"""Tests for triage report builder."""

import json
from pathlib import Path

from flink_stmt_triage.report import (
    build_hypotheses,
    build_triage_report,
    summarize_metric,
)
from flink_stmt_triage.tools import run_triage_dry_run

FIXTURES = Path(__file__).parent / "fixtures"


def test_summarize_metric_trend_rising():
    resp = json.loads((FIXTURES / "metric_records_in.json").read_text())
    summary = summarize_metric("num_records_in", resp)
    assert summary.latest == 400.0
    assert summary.trend == "rising"


def test_build_triage_report_running():
    data = run_triage_dry_run()
    report = build_triage_report(
        statement_name="perf-dml-passthrough",
        compute_pool_id="lfcp-example",
        statement=json.loads((FIXTURES / "statement_running.json").read_text()),
        exceptions=json.loads((FIXTURES / "exceptions_empty.json").read_text()),
        metric_responses={
            "num_records_in": json.loads((FIXTURES / "metric_records_in.json").read_text()),
            "num_records_out": json.loads(
                (FIXTURES / "metric_records_out.json").read_text()
            ),
            "pending_records": json.loads((FIXTURES / "metric_pending.json").read_text()),
        },
        pool_cfu=json.loads((FIXTURES / "metric_pool_cfu.json").read_text()),
    )
    assert report.phase == "RUNNING"
    assert report.severity == "info"
    md = report.to_markdown()
    assert "perf-dml-passthrough" in md
    assert "## Hypotheses" in md


def test_build_hypotheses_failed_with_exceptions():
    exc = [{"message": "parse error"}]
    hyps = build_hypotheses("FAILED", "detail", [], exc)
    assert any("parse error" in h.description for h in hyps)


def test_run_triage_dry_run_dict():
    data = run_triage_dry_run()
    assert data["phase"] == "RUNNING"
    assert data["statement_name"] == "perf-dml-passthrough"
