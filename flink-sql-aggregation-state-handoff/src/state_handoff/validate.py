"""Validate aggregate handoff totals against expected per-key sums."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from dotenv import load_dotenv

from state_handoff.produce import build_event


def compute_expected_totals(events: list[dict[str, Any]]) -> dict[str, int]:
    """Sum amount per device_id from a list of source events."""
    totals: dict[str, int] = {}
    for event in events:
        device_id = event["device_id"]
        totals[device_id] = totals.get(device_id, 0) + int(event["amount"])
    return totals


def merge_handoff_totals(
    baseline: dict[str, int],
    incremental_events: list[dict[str, Any]],
) -> dict[str, int]:
    """Merge v1 snapshot totals with incremental events after handoff."""
    merged = dict(baseline)
    for device_id, amount in compute_expected_totals(incremental_events).items():
        merged[device_id] = merged.get(device_id, 0) + amount
    return merged


def parse_sink_records(records: list[dict[str, Any]]) -> dict[str, int]:
    """Extract device_id → total_amount from upsert sink JSON records."""
    return {row["device_id"]: int(row["total_amount"]) for row in records}


def diff_totals(expected: dict[str, int], actual: dict[str, int]) -> list[dict[str, Any]]:
    """Return mismatches between expected and actual per-key totals."""
    all_keys = sorted(set(expected) | set(actual))
    diffs: list[dict[str, Any]] = []
    for key in all_keys:
        exp = expected.get(key, 0)
        act = actual.get(key, 0)
        if exp != act:
            diffs.append({"device_id": key, "expected": exp, "actual": act})
    return diffs


def expected_from_batches(
    batch_specs: list[tuple[int, int, int, int]],
) -> dict[str, int]:
    """Build expected totals from (count, num_keys, base_amount, start_seq) batch specs."""
    events: list[dict] = []
    for count, num_keys, base_amount, start_seq in batch_specs:
        for i in range(count):
            events.append(build_event(start_seq + i, num_keys, base_amount))
    return compute_expected_totals(events)


def main() -> None:
    """CLI entry: compare expected totals JSON vs actual sink JSON."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Validate handoff aggregate totals")
    parser.add_argument(
        "--baseline",
        help="JSON file: v1 sink records or device_id→total map",
    )
    parser.add_argument(
        "--incremental",
        help="JSON file: list of source events produced after handoff",
    )
    parser.add_argument(
        "--actual",
        required=True,
        help="JSON file: v2 sink records or device_id→total map",
    )
    parser.add_argument(
        "--expected",
        help="JSON file: precomputed device_id→total map (skips baseline+incremental)",
    )
    args = parser.parse_args()

    def _load(path: str) -> Any:
        return json.loads(open(path, encoding="utf-8").read())

    if args.expected:
        expected = _load(args.expected)
        if isinstance(expected, list):
            expected = parse_sink_records(expected)
    else:
        baseline_raw = _load(args.baseline) if args.baseline else {}
        if isinstance(baseline_raw, list):
            baseline = parse_sink_records(baseline_raw)
        else:
            baseline = {k: int(v) for k, v in baseline_raw.items()}
        incremental = _load(args.incremental) if args.incremental else []
        expected = merge_handoff_totals(baseline, incremental)

    actual_raw = _load(args.actual)
    if isinstance(actual_raw, list):
        actual = parse_sink_records(actual_raw)
    else:
        actual = {k: int(v) for k, v in actual_raw.items()}

    diffs = diff_totals(expected, actual)
    if diffs:
        print("Validation FAILED:")
        print(json.dumps(diffs, indent=2))
        sys.exit(1)
    print("Validation PASSED")
    print(json.dumps(expected, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
