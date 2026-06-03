"""Tests for Metrics API client."""

from unittest.mock import MagicMock, patch

import httpx

from flink_stmt_triage.config import TriageConfig
from flink_stmt_triage.metrics_client import MetricsClient, latest_value, query_metrics


def _cfg() -> TriageConfig:
    return TriageConfig(
        org_id="org-1",
        env_id="env-1",
        flink_api_key="fk",
        flink_api_secret="fs",
        cloud_provider="aws",
        cloud_region="us-east-1",
        compute_pool_id="lfcp-1",
        catalog_name="cat",
        database_name="db",
        telemetry_api_key="tk",
        telemetry_api_secret="ts",
    )


def test_query_metrics_posts_payload():
    cfg = _cfg()
    payload = {"aggregations": [{"metric": "m"}]}
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"data": []}
    mock_resp.raise_for_status = MagicMock()

    with patch("flink_stmt_triage.metrics_client.httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.return_value = mock_resp
        result = query_metrics(cfg, payload)

    instance.post.assert_called_once()
    call_kwargs = instance.post.call_args.kwargs
    assert call_kwargs["json"] == payload
    assert call_kwargs["auth"] == ("tk", "ts")
    assert result == {"data": []}


def test_latest_value_extracts_last_point():
    resp = {
        "data": [
            {
                "values": [
                    {"timestamp": "t1", "value": 1.0},
                    {"timestamp": "t2", "value": 42.0},
                ]
            }
        ]
    }
    assert latest_value(resp) == 42.0


def test_latest_value_empty():
    assert latest_value({}) is None


def test_metrics_client_raises_on_http_error():
    cfg = _cfg()
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "err", request=MagicMock(), response=MagicMock()
    )

    with patch("flink_stmt_triage.metrics_client.httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.return_value = mock_resp
        client = MetricsClient(cfg)
        try:
            client.query({})
            assert False, "expected HTTPStatusError"
        except httpx.HTTPStatusError:
            pass
