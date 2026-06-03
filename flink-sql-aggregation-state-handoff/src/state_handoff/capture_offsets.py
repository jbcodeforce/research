"""Parse Confluent Cloud Flink statement offsets for specific-offsets hints."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
from typing import Any

import requests
from dotenv import load_dotenv


def parse_latest_offsets(response: dict[str, Any], table_name: str) -> dict[int, int]:
    """Extract partition → offset map for a Flink table from statement status."""
    latest = response.get("status", {}).get("latest_offsets") or {}
    table_offsets = latest.get(table_name)
    if table_offsets is None:
        raise KeyError(f"No latest_offsets entry for table {table_name!r}")
    return {int(partition): int(offset) for partition, offset in table_offsets.items()}


def format_specific_offsets(partition_offsets: dict[int, int]) -> str:
    """Format partition offsets for Flink scan.startup.specific-offsets hint."""
    if not partition_offsets:
        return ""
    parts = [
        f"partition:{partition},offset:{offset}"
        for partition, offset in sorted(partition_offsets.items())
    ]
    return ";".join(parts)


def offsets_from_statement_response(response: dict[str, Any], table_name: str) -> str:
    """Build a specific-offsets hint string from a CC statement API response."""
    return format_specific_offsets(parse_latest_offsets(response, table_name))


def fetch_statement(org_id: str, env_id: str, statement_name: str) -> dict[str, Any]:
    """Fetch a Flink statement from the Confluent Cloud REST API."""
    region = os.environ.get("CLOUD_REGION", "us-east-1")
    api_key = os.environ["FLINK_API_KEY"]
    api_secret = os.environ["FLINK_API_SECRET"]
    token = base64.b64encode(f"{api_key}:{api_secret}".encode()).decode()
    url = (
        f"https://flink.{region}.aws.confluent.cloud/sql/v1/organizations/"
        f"{org_id}/environments/{env_id}/statements/{statement_name}"
    )
    response = requests.get(
        url,
        headers={"Authorization": f"Basic {token}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def main() -> None:
    """CLI entry: print specific-offsets hint for device_events from a stopped statement."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Capture CC Flink latest_offsets as specific-offsets hint")
    parser.add_argument(
        "--statement",
        default=os.environ.get("STATEMENT_DML_V1", "handoff-dml-v1"),
        help="Stopped v1 DML statement name",
    )
    parser.add_argument(
        "--table",
        default="device_events",
        help="Flink table name in latest_offsets",
    )
    parser.add_argument(
        "--json-file",
        help="Use a saved statement JSON response instead of live API",
    )
    args = parser.parse_args()

    if args.json_file:
        payload = json.loads(open(args.json_file, encoding="utf-8").read())
    else:
        payload = fetch_statement(
            os.environ["CC_ORG_ID"],
            os.environ["CC_ENV_ID"],
            args.statement,
        )

    hint = offsets_from_statement_response(payload, args.table)
    if not hint:
        print("No offsets found", file=sys.stderr)
        sys.exit(1)
    print(hint)


if __name__ == "__main__":
    main()
