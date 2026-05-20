"""Feature window computation tests."""

from datetime import datetime, timedelta, timezone

from reefer_pm_kafka.features import build_feature_rows, compute_features


def _event(
    device: str,
    second: int,
    *,
    split: str = "train",
    label: str = "healthy",
    return_temp: float = 3.0,
):
    ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc) + timedelta(seconds=second)
    return {
        "event_id": f"e-{device}-{second}",
        "device_id": device,
        "event_time": ts.isoformat().replace("+00:00", "Z"),
        "return_air_temp_c": return_temp,
        "supply_air_temp_c": 1.0,
        "compressor_runtime_h": 1000.0,
        "door_open_count": 1,
        "power_draw_kw": 6.0,
        "vibration_rms": 0.2,
        "meta": {"split": split, "is_labeled": label is not None},
        "label": {"failure_class": label, "horizon_hours": 24 if label else None},
    }


def test_compute_features_slope():
    events = [_event("reefer_01", s, return_temp=3.0 + s * 0.5) for s in range(10)]
    row = compute_features(events, window_seconds=60)
    assert row is not None
    assert row.features["avg_return_air_temp_c"] > 3.0
    assert row.features["slope_return_air_per_min"] > 0


def test_build_feature_rows_filters_split():
    records = [
        _event("reefer_01", 0, split="train"),
        _event("reefer_03", 1, split="test"),
    ]
    rows = build_feature_rows(records, window_seconds=60, split_filter="train")
    assert len(rows) == 1
    assert rows[0].device_id == "reefer_01"
