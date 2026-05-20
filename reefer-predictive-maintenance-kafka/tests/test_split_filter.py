"""Train/test device holdout and leakage tests."""

from reefer_pm_kafka.config import load_generator_config
from reefer_pm_kafka.features import build_feature_rows
from reefer_pm_kafka.generator import generate_records


def test_no_test_devices_in_train_features():
    cfg = load_generator_config()
    records = list(generate_records(cfg))
    train_devices = set(cfg.train_devices)
    test_devices = set(cfg.test_devices)

    rows = build_feature_rows(
        records,
        window_seconds=10,
        split_filter="train",
        device_allowlist=train_devices,
        device_denylist=test_devices,
    )

    device_ids = {r.device_id for r in rows}
    assert device_ids.isdisjoint(test_devices)
    assert device_ids.issubset(train_devices)


def test_test_split_only_test_device():
    cfg = load_generator_config()
    records = list(generate_records(cfg))
    test_devices = set(cfg.test_devices)

    rows = build_feature_rows(
        records,
        window_seconds=10,
        split_filter="test",
        device_allowlist=test_devices,
    )

    assert all(r.device_id in test_devices for r in rows)
    assert all(r.meta_split == "test" for r in rows)


def test_unified_topic_has_mixed_splits():
    cfg = load_generator_config()
    records = list(generate_records(cfg))
    splits = {r["meta"]["split"] for r in records}
    assert splits == {"train", "test", "inference"}
