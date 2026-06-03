"""Build Confluent Cloud Metrics API query payloads for Flink statements."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def _iso_interval(start: datetime, end: datetime) -> str:
    return f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"


def _statement_filters(statement_name: str, compute_pool_id: str) -> list[dict[str, Any]]:
    """Return AND filters for statement + compute pool."""
    filters: list[dict[str, Any]] = [
        {
            "field": "resource.flink_statement.name",
            "op": "EQ",
            "value": statement_name,
        },
    ]
    if compute_pool_id:
        filters.append(
            {
                "field": "resource.compute_pool.id",
                "op": "EQ",
                "value": compute_pool_id,
            }
        )
    return filters


def build_metric_query(
    metric: str,
    *,
    statement_name: str,
    compute_pool_id: str,
    window_minutes: int = 30,
    granularity: str = "PT1M",
    limit: int = 60,
    end: datetime | None = None,
) -> dict[str, Any]:
    """Build a Metrics API query payload for one Flink metric."""
    end_time = end or datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=window_minutes)
    return {
        "aggregations": [{"metric": metric}],
        "filter": {"op": "AND", "filters": _statement_filters(statement_name, compute_pool_id)},
        "granularity": granularity,
        "intervals": [_iso_interval(start_time, end_time)],
        "limit": limit,
    }


def records_in_query(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, Any]:
    return build_metric_query(
        "io.confluent.flink/num_records_in",
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        window_minutes=window_minutes,
    )


def records_out_query(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, Any]:
    return build_metric_query(
        "io.confluent.flink/num_records_out",
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        window_minutes=window_minutes,
    )


def pending_records_query(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, Any]:
    return build_metric_query(
        "io.confluent.flink/pending_records",
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        window_minutes=window_minutes,
    )


def statement_status_query(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, Any]:
    return build_metric_query(
        "io.confluent.flink/statement_status",
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        window_minutes=window_minutes,
    )


def state_size_query(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, Any]:
    return build_metric_query(
        "io.confluent.flink/operator/state_size_bytes",
        statement_name=statement_name,
        compute_pool_id=compute_pool_id,
        window_minutes=window_minutes,
    )


def pool_cfu_query(compute_pool_id: str, window_minutes: int = 30) -> dict[str, Any]:
    """Query current CFUs for a compute pool (no statement filter)."""
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=window_minutes)
    return {
        "aggregations": [{"metric": "io.confluent.flink/compute_pool_utilization/current_cfus"}],
        "filter": {
            "op": "AND",
            "filters": [
                {
                    "field": "resource.compute_pool.id",
                    "op": "EQ",
                    "value": compute_pool_id,
                }
            ],
        },
        "granularity": "PT1M",
        "intervals": [_iso_interval(start_time, end_time)],
        "limit": 60,
    }


def pool_cfu_limit_query(compute_pool_id: str, window_minutes: int = 30) -> dict[str, Any]:
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=window_minutes)
    return {
        "aggregations": [{"metric": "io.confluent.flink/compute_pool_utilization/cfu_limit"}],
        "filter": {
            "op": "AND",
            "filters": [
                {
                    "field": "resource.compute_pool.id",
                    "op": "EQ",
                    "value": compute_pool_id,
                }
            ],
        },
        "granularity": "PT1M",
        "intervals": [_iso_interval(start_time, end_time)],
        "limit": 60,
    }


def all_statement_metrics_queries(
    statement_name: str, compute_pool_id: str, window_minutes: int = 30
) -> dict[str, dict[str, Any]]:
    """Return named query payloads for a full statement metrics snapshot."""
    return {
        "num_records_in": records_in_query(statement_name, compute_pool_id, window_minutes),
        "num_records_out": records_out_query(statement_name, compute_pool_id, window_minutes),
        "pending_records": pending_records_query(statement_name, compute_pool_id, window_minutes),
        "statement_status": statement_status_query(
            statement_name, compute_pool_id, window_minutes
        ),
        "state_size_bytes": state_size_query(statement_name, compute_pool_id, window_minutes),
    }
