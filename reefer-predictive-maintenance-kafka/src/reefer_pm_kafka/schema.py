"""Telemetry and feature record validation."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from reefer_pm_kafka.config import FAILURE_CLASSES, SPLITS

REQUIRED_TELEMETRY_FIELDS = (
    "event_id",
    "device_id",
    "event_time",
    "return_air_temp_c",
    "supply_air_temp_c",
    "compressor_runtime_h",
    "door_open_count",
    "power_draw_kw",
    "vibration_rms",
    "meta",
    "label",
)


def _parse_iso8601(value: str) -> datetime:
    """Parse ISO-8601 timestamps with Z or offset."""
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def validate_telemetry(record: dict[str, Any]) -> list[str]:
    """Return validation errors; empty list means valid."""
    errors: list[str] = []
    for field in REQUIRED_TELEMETRY_FIELDS:
        if field not in record:
            errors.append(f"missing field: {field}")

    if errors:
        return errors

    meta = record.get("meta") or {}
    label = record.get("label") or {}
    split = meta.get("split")
    if split not in SPLITS:
        errors.append(f"meta.split must be one of {SPLITS}, got {split!r}")

    is_labeled = meta.get("is_labeled")
    if not isinstance(is_labeled, bool):
        errors.append("meta.is_labeled must be boolean")

    failure_class = label.get("failure_class")
    if is_labeled:
        if failure_class not in FAILURE_CLASSES:
            errors.append(f"label.failure_class must be one of {FAILURE_CLASSES}")
    elif failure_class is not None:
        errors.append("unlabeled records must have label.failure_class null")

    try:
        _parse_iso8601(str(record["event_time"]))
    except (TypeError, ValueError) as exc:
        errors.append(f"invalid event_time: {exc}")

    numeric_fields = (
        "return_air_temp_c",
        "supply_air_temp_c",
        "compressor_runtime_h",
        "power_draw_kw",
        "vibration_rms",
    )
    for name in numeric_fields:
        try:
            float(record[name])
        except (TypeError, ValueError):
            errors.append(f"{name} must be numeric")

    try:
        int(record["door_open_count"])
    except (TypeError, ValueError):
        errors.append("door_open_count must be int")

    return errors


def new_event_id() -> str:
    return str(uuid.uuid4())


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_event_time(record: dict[str, Any]) -> datetime:
    """Parse event_time from a validated telemetry record."""
    return _parse_iso8601(str(record["event_time"]))


def window_start_for(ts: datetime, window_seconds: int) -> datetime:
    """Floor timestamp to tumbling window start (UTC)."""
    epoch = int(ts.timestamp())
    start_epoch = (epoch // window_seconds) * window_seconds
    return datetime.fromtimestamp(start_epoch, tz=timezone.utc)


def majority_label(labels: list[str | None]) -> str | None:
    """Pick the most common non-null failure class in a window."""
    filtered = [lbl for lbl in labels if lbl in FAILURE_CLASSES]
    if not filtered:
        return None
    return max(set(filtered), key=filtered.count)
