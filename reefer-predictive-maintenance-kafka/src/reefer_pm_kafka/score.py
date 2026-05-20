"""Score inference split from unified telemetry topic."""

from __future__ import annotations

import argparse
import json
import logging

from reefer_pm_kafka.config import load_generator_config, load_settings
from reefer_pm_kafka.features import build_feature_rows
from reefer_pm_kafka.kafka_utils import consume_all_json, create_producer, ensure_topics, publish_json
from reefer_pm_kafka.model_utils import load_model, predict_row
from reefer_pm_kafka.schema import utc_now_iso, validate_telemetry

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Score inference split from Kafka")
    parser.add_argument("--from-file", metavar="PATH", help="Score from JSONL instead of Kafka")
    args = parser.parse_args()

    settings = load_settings()
    gen_cfg = load_generator_config()
    inference_devices = set(gen_cfg.inference_devices)

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
            group_id="reefer-pm-score",
        )
        valid = [rec for rec in raw if not validate_telemetry(rec)]

    rows = build_feature_rows(
        valid,
        settings.window_seconds,
        split_filter="inference",
        device_allowlist=inference_devices,
    )
    if not rows:
        raise SystemExit("no inference windows; run reefer-pm-generate first")

    ensure_topics(settings.bootstrap_servers, [settings.topic_predictions])
    producer = create_producer(settings.bootstrap_servers)
    scored = 0
    for row in rows:
        predicted, confidence = predict_row(pipe, row)
        payload = {
            "device_id": row.device_id,
            "scored_at": utc_now_iso(),
            "model_version": version,
            "predicted_class": predicted,
            "confidence": confidence,
            "feature_ref": {
                "window_start": row.window_start.isoformat().replace("+00:00", "Z"),
                "window_end": row.window_end.isoformat().replace("+00:00", "Z"),
            },
        }
        publish_json(producer, settings.topic_predictions, row.device_id, payload)
        scored += 1

    producer.flush(30)
    logger.info("published %d predictions to %s", scored, settings.topic_predictions)


if __name__ == "__main__":
    main()
