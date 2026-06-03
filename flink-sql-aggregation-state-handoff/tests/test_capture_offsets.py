"""Tests for offset capture helpers."""

import json
from pathlib import Path

import pytest

from state_handoff.capture_offsets import (
    format_specific_offsets,
    parse_latest_offsets,
    offsets_from_statement_response,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def statement_response() -> dict:
    return json.loads((FIXTURES / "statement_latest_offsets.json").read_text())


def test_parse_latest_offsets_extracts_partition_offsets(statement_response):
    offsets = parse_latest_offsets(statement_response, table_name="device_events")
    assert offsets == {0: 42, 1: 17, 2: 0}


def test_format_specific_offsets_produces_flink_hint():
    hint = format_specific_offsets({0: 42, 1: 17, 2: 0})
    assert hint == "partition:0,offset:42;partition:1,offset:17;partition:2,offset:0"


def test_format_specific_offsets_empty():
    assert format_specific_offsets({}) == ""


def test_format_specific_offsets_sorts_partitions():
    hint = format_specific_offsets({2: 1, 0: 5})
    assert hint == "partition:0,offset:5;partition:2,offset:1"


def test_offsets_from_statement_response_roundtrip(statement_response):
    hint = offsets_from_statement_response(statement_response, "device_events")
    assert "partition:0,offset:42" in hint
    assert "partition:1,offset:17" in hint
