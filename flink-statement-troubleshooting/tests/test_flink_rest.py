"""Tests for Flink REST client."""

from unittest.mock import MagicMock, patch

from flink_stmt_triage.config import TriageConfig
from flink_stmt_triage.flink_rest import FlinkRestClient, statement_phase


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


def test_get_statement_url_and_auth():
    cfg = _cfg()
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"name": "s1", "status": {"phase": "RUNNING"}}
    mock_resp.raise_for_status = MagicMock()

    with patch("flink_stmt_triage.flink_rest.httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = mock_resp
        result = FlinkRestClient(cfg).get_statement("s1")

    url = instance.get.call_args.args[0]
    assert "/organizations/org-1/environments/env-1/statements/s1" in url
    assert instance.get.call_args.kwargs["auth"] == ("fk", "fs")
    assert statement_phase(result) == "RUNNING"


def test_get_exceptions_404_returns_empty():
    cfg = _cfg()
    mock_resp = MagicMock()
    mock_resp.status_code = 404

    with patch("flink_stmt_triage.flink_rest.httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = mock_resp
        result = FlinkRestClient(cfg).get_exceptions("missing")

    assert result == {"exceptions": []}
