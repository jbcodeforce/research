"""End-to-end ML path without Kafka."""

from pathlib import Path

from reefer_pm_kafka.config import load_generator_config
from reefer_pm_kafka.features import build_feature_rows
from reefer_pm_kafka.generator import generate_records
from reefer_pm_kafka.model_utils import evaluate_predictions, predict_row, save_model, train_model, load_model


def test_train_eval_score_offline(tmp_path: Path):
    cfg = load_generator_config()
    records = list(generate_records(cfg))
    window_seconds = 10

    train_devices = set(cfg.train_devices)
    test_devices = set(cfg.test_devices)

    train_rows = build_feature_rows(
        records,
        window_seconds,
        split_filter="train",
        device_allowlist=train_devices,
        device_denylist=test_devices,
    )
    assert len(train_rows) >= 30

    pipe, _meta = train_model(train_rows)
    model_path = tmp_path / "reefer_pm_v001.joblib"
    save_model(pipe, model_path, version="v001")

    test_rows = build_feature_rows(
        records,
        window_seconds,
        split_filter="test",
        device_allowlist=test_devices,
    )
    labeled = [r for r in test_rows if r.label]
    assert labeled

    y_true, y_pred = [], []
    loaded, version, _ = load_model(model_path)
    assert version == "v001"
    for row in labeled:
        pred, conf = predict_row(loaded, row)
        assert conf > 0
        y_true.append(row.label)  # type: ignore[arg-type]
        y_pred.append(pred)

    metrics = evaluate_predictions(y_true, y_pred)
    assert metrics["f1_macro"] >= 0.5
