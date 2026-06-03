"""Load configuration from environment and .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_PROJECT_DIR = Path(__file__).resolve().parent.parent.parent


def load_dotenv_file() -> None:
    """Load project .env when present."""
    env_path = _PROJECT_DIR / ".env"
    if env_path.is_file():
        load_dotenv(env_path, override=False)


@dataclass(frozen=True)
class TriageConfig:
    """Runtime configuration for Flink REST and Metrics API."""

    org_id: str
    env_id: str
    flink_api_key: str
    flink_api_secret: str
    cloud_provider: str
    cloud_region: str
    compute_pool_id: str
    catalog_name: str
    database_name: str
    telemetry_api_key: str
    telemetry_api_secret: str
    telemetry_endpoint: str = "https://api.telemetry.confluent.cloud"
    flink_endpoint: str | None = None

    @property
    def flink_base_url(self) -> str:
        """Flink SQL REST base URL (no /sql/v1 suffix)."""
        if self.flink_endpoint:
            return self.flink_endpoint.rstrip("/")
        return (
            f"https://flink.{self.cloud_region}.{self.cloud_provider}.confluent.cloud"
        )

    @property
    def statements_url_prefix(self) -> str:
        return (
            f"/sql/v1/organizations/{self.org_id}/environments/{self.env_id}/statements"
        )


def get_config() -> TriageConfig:
    """Build config from environment; raises ValueError when required keys missing."""
    load_dotenv_file()
    missing = []
    required = {
        "CC_ORG_ID": "org_id",
        "CC_ENV_ID": "env_id",
        "FLINK_API_KEY": "flink_api_key",
        "FLINK_API_SECRET": "flink_api_secret",
    }
    values: dict[str, str] = {}
    for env_key, _ in required.items():
        val = os.getenv(env_key, "").strip()
        if not val:
            missing.append(env_key)
        values[env_key] = val

    if missing:
        raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

    telemetry_key = os.getenv("TELEMETRY_API_KEY", "").strip() or values["FLINK_API_KEY"]
    telemetry_secret = (
        os.getenv("TELEMETRY_API_SECRET", "").strip() or os.getenv("FLINK_API_SECRET", "")
    )

    return TriageConfig(
        org_id=values["CC_ORG_ID"],
        env_id=values["CC_ENV_ID"],
        flink_api_key=values["FLINK_API_KEY"],
        flink_api_secret=values["FLINK_API_SECRET"],
        cloud_provider=os.getenv("FLINK_CLOUD_PROVIDER", "aws"),
        cloud_region=os.getenv("FLINK_CLOUD_REGION", "us-east-1"),
        compute_pool_id=os.getenv("FLINK_COMPUTE_POOL_ID", ""),
        catalog_name=os.getenv("FLINK_CATALOG_NAME", ""),
        database_name=os.getenv("FLINK_DATABASE_NAME", ""),
        telemetry_api_key=telemetry_key,
        telemetry_api_secret=telemetry_secret,
        flink_endpoint=os.getenv("FLINK_REST_ENDPOINT") or None,
    )


def try_get_config() -> TriageConfig | None:
    """Return config or None when credentials are not set."""
    try:
        return get_config()
    except ValueError:
        return None
