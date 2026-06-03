"""Tests for Metrics API query payload builders."""

from flink_stmt_triage.flink_queries import (
    all_statement_metrics_queries,
    build_metric_query,
    pool_cfu_query,
    records_in_query,
)


def test_records_in_query_filters():
    payload = records_in_query("perf-dml-passthrough", "lfcp-abc", window_minutes=15)
    assert payload["aggregations"][0]["metric"] == "io.confluent.flink/num_records_in"
    filters = payload["filter"]["filters"]
    names = {f["field"]: f["value"] for f in filters}
    assert names["resource.flink_statement.name"] == "perf-dml-passthrough"
    assert names["resource.compute_pool.id"] == "lfcp-abc"
    assert payload["granularity"] == "PT1M"
    assert payload["limit"] == 60


def test_build_metric_query_interval():
    from datetime import datetime, timezone

    end = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
    payload = build_metric_query(
        "io.confluent.flink/pending_records",
        statement_name="stmt-1",
        compute_pool_id="lfcp-1",
        window_minutes=5,
        end=end,
    )
    assert payload["intervals"] == ["2026-06-02T11:55:00Z/2026-06-02T12:00:00Z"]


def test_all_statement_metrics_queries_keys():
    queries = all_statement_metrics_queries("s1", "p1")
    assert set(queries.keys()) == {
        "num_records_in",
        "num_records_out",
        "pending_records",
        "statement_status",
        "state_size_bytes",
    }


def test_pool_cfu_query_no_statement_filter():
    payload = pool_cfu_query("lfcp-xyz")
    filters = payload["filter"]["filters"]
    assert len(filters) == 1
    assert filters[0]["field"] == "resource.compute_pool.id"
