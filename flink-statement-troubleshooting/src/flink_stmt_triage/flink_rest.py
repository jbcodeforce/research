"""Flink SQL REST client for statement status and exceptions."""

from __future__ import annotations

from typing import Any

import httpx

from flink_stmt_triage.config import TriageConfig


class FlinkRestClient:
    """Read-only Flink SQL REST operations."""

    def __init__(self, config: TriageConfig) -> None:
        self._config = config
        self._base = config.flink_base_url

    def _auth(self) -> tuple[str, str]:
        return self._config.flink_api_key, self._config.flink_api_secret

    def _url(self, path: str) -> str:
        return f"{self._base}{path}"

    def get_statement(self, statement_name: str) -> dict[str, Any]:
        """GET statement by name."""
        path = f"{self._config.statements_url_prefix}/{statement_name}"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(self._url(path), auth=self._auth())
            resp.raise_for_status()
            return resp.json()

    def get_exceptions(self, statement_name: str) -> dict[str, Any]:
        """GET recent exceptions for a statement."""
        path = f"{self._config.statements_url_prefix}/{statement_name}/exceptions"
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(self._url(path), auth=self._auth())
            if resp.status_code == 404:
                return {"exceptions": []}
            resp.raise_for_status()
            return resp.json()

    def list_statements(self, page_size: int = 50) -> dict[str, Any]:
        """GET first page of statements."""
        path = self._config.statements_url_prefix
        with httpx.Client(timeout=60.0) as client:
            resp = client.get(
                self._url(path),
                auth=self._auth(),
                params={"page_size": page_size},
            )
            resp.raise_for_status()
            return resp.json()


def statement_phase(statement: dict[str, Any]) -> str:
    """Extract phase string from statement JSON."""
    status = statement.get("status") or {}
    return str(status.get("phase", "UNKNOWN"))


def statement_detail(statement: dict[str, Any]) -> str:
    status = statement.get("status") or {}
    return str(status.get("detail", ""))
