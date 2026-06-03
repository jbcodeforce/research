"""Client for Confluent Cloud Metrics API."""

from __future__ import annotations

from typing import Any

import httpx

from flink_stmt_triage.config import TriageConfig


class MetricsClient:
    """POST metric queries to the telemetry API."""

    def __init__(self, config: TriageConfig) -> None:
        self._config = config
        self._url = f"{config.telemetry_endpoint.rstrip('/')}/v2/metrics/cloud/query"

    def query(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Execute one metrics query and return parsed JSON."""
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(
                self._url,
                json=payload,
                auth=(self._config.telemetry_api_key, self._config.telemetry_api_secret),
                headers={"Content-Type": "application/json"},
            )
            resp.raise_for_status()
            return resp.json()


def query_metrics(config: TriageConfig, payload: dict[str, Any]) -> dict[str, Any]:
    """Functional wrapper for a single metrics query."""
    return MetricsClient(config).query(payload)


def latest_value(metric_response: dict[str, Any]) -> float | None:
    """Extract the most recent numeric value from a metrics API response."""
    data = metric_response.get("data") or []
    if not data:
        return None
    points = data[0].get("values") or []
    if not points:
        return None
    return points[-1].get("value")
