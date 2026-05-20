"""Schema validation tests."""

from reefer_pm_kafka.schema import validate_telemetry


def _valid_record(**overrides):
    base = {
        "event_id": "e1",
        "device_id": "reefer_01",
        "event_time": "2026-01-15T12:00:00Z",
        "return_air_temp_c": 3.0,
        "supply_air_temp_c": 1.0,
        "compressor_runtime_h": 1000.0,
        "door_open_count": 0,
        "power_draw_kw": 6.0,
        "vibration_rms": 0.2,
        "meta": {"split": "train", "is_labeled": True},
        "label": {"failure_class": "healthy", "horizon_hours": 24},
    }
    base.update(overrides)
    return base


def test_valid_train_record():
    assert validate_telemetry(_valid_record()) == []


def test_missing_field():
    rec = _valid_record()
    del rec["device_id"]
    assert any("device_id" in e for e in validate_telemetry(rec))


def test_invalid_split():
    rec = _valid_record(meta={"split": "holdout", "is_labeled": True})
    assert any("meta.split" in e for e in validate_telemetry(rec))


def test_inference_unlabeled():
    rec = _valid_record(
        meta={"split": "inference", "is_labeled": False},
        label={"failure_class": None, "horizon_hours": None},
    )
    assert validate_telemetry(rec) == []


def test_inference_with_label_rejected():
    rec = _valid_record(
        meta={"split": "inference", "is_labeled": False},
        label={"failure_class": "healthy", "horizon_hours": 24},
    )
    assert any("failure_class" in e for e in validate_telemetry(rec))
