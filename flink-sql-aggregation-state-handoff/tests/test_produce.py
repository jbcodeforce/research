"""Tests for event producer helpers."""

from state_handoff.produce import build_event, device_id_for_index, event_payload


def test_device_id_for_index_cycles_keys():
    assert device_id_for_index(0, num_keys=5) == "device-1"
    assert device_id_for_index(4, num_keys=5) == "device-5"
    assert device_id_for_index(5, num_keys=5) == "device-1"


def test_build_event_schema():
    event = build_event(seq=3, num_keys=5, base_amount=10)
    assert event["device_id"] == "device-4"
    assert event["amount"] == 13
    assert event["seq"] == 3
    assert "event_time" in event


def test_event_payload_serializes_json_bytes():
    payload = event_payload(build_event(1, 3, 100))
    assert b'"device_id"' in payload
    assert b'"amount"' in payload
