"""Windowed feature extraction shared by train, evaluate, and score."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np

from reefer_pm_kafka.config import FEATURE_COLUMNS
from reefer_pm_kafka.schema import majority_label, parse_event_time, window_start_for


@dataclass
class FeatureRow:
    device_id: str
    window_start: datetime
    window_end: datetime
    meta_split: str
    label: str | None
    features: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "window_start": self.window_start.isoformat().replace("+00:00", "Z"),
            "window_end": self.window_end.isoformat().replace("+00:00", "Z"),
            "meta": {"split": self.meta_split},
            "label": {"failure_class": self.label},
            "feature_vector": self.features,
        }


def compute_features(
    events: list[dict[str, Any]],
    window_seconds: int,
) -> FeatureRow | None:
    """Aggregate one device's events in a single tumbling window."""
    if not events:
        return None

    device_id = str(events[0]["device_id"])
    window_start = window_start_for(parse_event_time(events[0]), window_seconds)
    window_end = window_start + timedelta(seconds=window_seconds)

    return_temps = [float(e["return_air_temp_c"]) for e in events]
    supply_temps = [float(e["supply_air_temp_c"]) for e in events]
    power = [float(e["power_draw_kw"]) for e in events]
    vibration = [float(e["vibration_rms"]) for e in events]
    doors = [int(e["door_open_count"]) for e in events]

    times_min = np.array(
        [(parse_event_time(e) - window_start).total_seconds() / 60.0 for e in events],
        dtype=float,
    )
    slope = 0.0
    if len(times_min) >= 2 and np.std(times_min) > 0:
        slope = float(np.polyfit(times_min, return_temps, 1)[0])

    deltas = [s - r for s, r in zip(supply_temps, return_temps)]
    labels = [
        (e.get("label") or {}).get("failure_class")
        for e in events
    ]
    meta_split = str((events[-1].get("meta") or {}).get("split", ""))

    features = {
        "avg_return_air_temp_c": float(np.mean(return_temps)),
        "std_return_air_temp_c": float(np.std(return_temps)),
        "delta_supply_return_c": float(np.mean(deltas)),
        "slope_return_air_per_min": slope,
        "avg_power_draw_kw": float(np.mean(power)),
        "max_door_open_count": float(max(doors)),
        "avg_vibration_rms": float(np.mean(vibration)),
    }

    return FeatureRow(
        device_id=device_id,
        window_start=window_start,
        window_end=window_end,
        meta_split=meta_split,
        label=majority_label(labels),
        features=features,
    )


def build_feature_rows(
    records: list[dict[str, Any]],
    window_seconds: int,
    *,
    split_filter: str | None = None,
    device_allowlist: set[str] | None = None,
    device_denylist: set[str] | None = None,
) -> list[FeatureRow]:
    """Group telemetry by device and window, then compute features."""
    filtered: list[dict[str, Any]] = []
    for rec in records:
        meta = rec.get("meta") or {}
        split = meta.get("split")
        device_id = str(rec.get("device_id", ""))
        if split_filter is not None and split != split_filter:
            continue
        if device_allowlist is not None and device_id not in device_allowlist:
            continue
        if device_denylist is not None and device_id in device_denylist:
            continue
        filtered.append(rec)

    buckets: dict[tuple[str, datetime], list[dict[str, Any]]] = defaultdict(list)
    for rec in filtered:
        ts = parse_event_time(rec)
        wstart = window_start_for(ts, window_seconds)
        buckets[(str(rec["device_id"]), wstart)].append(rec)

    rows: list[FeatureRow] = []
    for (_device, _wstart), events in sorted(buckets.items()):
        events.sort(key=lambda e: parse_event_time(e))
        row = compute_features(events, window_seconds)
        if row is not None:
            rows.append(row)
    return rows


def feature_matrix(rows: list[FeatureRow]) -> tuple[np.ndarray, list[str]]:
    """Convert feature rows to X and parallel label list."""
    if not rows:
        return np.empty((0, len(FEATURE_COLUMNS))), []
    x = np.array([[r.features[col] for col in FEATURE_COLUMNS] for r in rows])
    labels = [r.label or "" for r in rows]
    return x, labels
