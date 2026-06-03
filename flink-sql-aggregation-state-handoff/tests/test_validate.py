"""Tests for aggregate validation helpers."""

import pytest

from state_handoff.validate import (
    compute_expected_totals,
    diff_totals,
    merge_handoff_totals,
    parse_sink_records,
)


def test_compute_expected_totals_sums_by_device():
    events = [
        {"device_id": "device-1", "amount": 10},
        {"device_id": "device-2", "amount": 5},
        {"device_id": "device-1", "amount": 3},
    ]
    assert compute_expected_totals(events) == {"device-1": 13, "device-2": 5}


def test_merge_handoff_totals_adds_baseline_and_incremental():
    baseline = {"device-1": 100, "device-2": 50}
    incremental = [{"device_id": "device-1", "amount": 7}, {"device_id": "device-3", "amount": 2}]
    assert merge_handoff_totals(baseline, incremental) == {
        "device-1": 107,
        "device-2": 50,
        "device-3": 2,
    }


def test_parse_sink_records_reads_upsert_values():
    records = [
        {"device_id": "device-1", "total_amount": 100, "last_event_time": "2026-01-01T00:00:00.000"},
        {"device_id": "device-2", "total_amount": 50, "last_event_time": "2026-01-01T00:00:01.000"},
    ]
    assert parse_sink_records(records) == {"device-1": 100, "device-2": 50}


def test_diff_totals_reports_mismatches():
    diffs = diff_totals({"device-1": 10}, {"device-1": 11, "device-2": 0})
    assert diffs == [{"device_id": "device-1", "expected": 10, "actual": 11}]


def test_diff_totals_empty_when_match():
    assert diff_totals({"device-1": 10}, {"device-1": 10}) == []
