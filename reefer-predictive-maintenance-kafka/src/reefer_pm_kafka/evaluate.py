"""Evaluate model on test split from the same telemetry topic."""

from __future__ import annotations

import argparse
import json
import logging
import uuid

from reefer_pm_kafka.config import FAILURE_CLASSES, load_generator_config, load_settings
from reefer_pm_kafka.features import build_feature_rows
from reefer_pm_kafka.kafka_utils import consume_all_json, create_producer, ensure_topics, publish_json
from reefer_pm_kafka.model_utils import evaluate_predictions, load_model, predict_row
from reefer_pm_kafka.schema import validate_telemetry

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Evaluate reefer PM model on test split")
    parser.add_argument("--from-file", metavar="PATH", help="Evaluate from JSONL instead of Kafka")
    args = parser.parse_args()

    settings = load_settings()
    gen_cfg = load_generator_config()
    test_devices = set(gen_cfg.test_devices)

    if not settings.model_path.exists():
        raise SystemExit(f"model not found: {settings.model_path}. Run reefer-pm-train first.")

    pipe, version, _cols = load_model(settings.model_path)

    if args.from_file:
        import pathlib

        valid = [json.loads(line) for line in pathlib.Path(args.from_file).read_text().splitlines() if line.strip()]
    else:
        raw = consume_all_json(
            settings.bootstrap_servers,
            settings.topic_telemetry,
            group_id="reefer-pm-eval",
        )
        valid = []
        for rec in raw:
            if not validate_telemetry(rec):
                valid.append(rec)

    rows = build_feature_rows(
        valid,
        settings.window_seconds,
        split_filter="test",
        device_allowlist=test_devices,
    )
    labeled = [r for r in rows if r.label in FAILURE_CLASSES]
    if not labeled:
        raise SystemExit("no labeled test windows; run reefer-pm-generate first")

    y_true: list[str] = []
    y_pred: list[str] = []
    for row in labeled:
        pred, _conf = predict_row(pipe, row)
        y_true.append(row.label)  # type: ignore[arg-type]
        y_pred.append(pred)

    metrics = evaluate_predictions(y_true, y_pred)
    logger.info(
        "test macro-F1=%.3f accuracy=%.3f (n=%d)",
        metrics["f1_macro"],
        metrics["accuracy"],
        len(labeled),
    )

    if metrics["f1_macro"] < 0.5:
        logger.warning("macro-F1 below 0.5 threshold from SPEC")

    payload = {
        "run_id": str(uuid.uuid4()),
        "model_version": version,
        "split": "test",
        "metrics": metrics,
    }

    ensure_topics(settings.bootstrap_servers, [settings.topic_metrics])
    producer = create_producer(settings.bootstrap_servers)
    publish_json(producer, settings.topic_metrics, version, payload)
    producer.flush(30)
    logger.info("published metrics to %s", settings.topic_metrics)


if __name__ == "__main__":
    main()
