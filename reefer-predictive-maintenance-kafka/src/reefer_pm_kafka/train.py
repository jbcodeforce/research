"""Train predictive maintenance model from train split on unified telemetry topic."""

from __future__ import annotations

import argparse
import json
import logging

from reefer_pm_kafka.config import FAILURE_CLASSES, load_generator_config, load_settings
from reefer_pm_kafka.features import build_feature_rows
from reefer_pm_kafka.kafka_utils import consume_all_json, create_producer, ensure_topics, publish_json
from reefer_pm_kafka.model_utils import save_model, train_model
from reefer_pm_kafka.schema import validate_telemetry

logger = logging.getLogger(__name__)


def load_telemetry_train_rows(
    bootstrap_servers: str,
    topic: str,
    window_seconds: int,
    train_devices: set[str],
    test_devices: set[str],
) -> list:
    """Consume telemetry and build feature rows for train split only."""
    raw = consume_all_json(
        bootstrap_servers,
        topic,
        group_id="reefer-pm-train",
    )
    valid: list[dict] = []
    for rec in raw:
        errors = validate_telemetry(rec)
        if errors:
            logger.warning("skip invalid record: %s", errors)
            continue
        valid.append(rec)

    return build_feature_rows(
        valid,
        window_seconds,
        split_filter="train",
        device_allowlist=train_devices,
        device_denylist=test_devices,
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Train reefer PM model from Kafka train split")
    parser.add_argument(
        "--from-file",
        metavar="PATH",
        help="Train from JSONL file instead of Kafka (for offline tests)",
    )
    args = parser.parse_args()

    settings = load_settings()
    gen_cfg = load_generator_config()
    train_devices = set(gen_cfg.train_devices)
    test_devices = set(gen_cfg.test_devices)

    if args.from_file:
        import pathlib

        valid = []
        for line in pathlib.Path(args.from_file).read_text(encoding="utf-8").splitlines():
            if line.strip():
                valid.append(json.loads(line))
        rows = build_feature_rows(
            valid,
            settings.window_seconds,
            split_filter="train",
            device_allowlist=train_devices,
            device_denylist=test_devices,
        )
    else:
        rows = load_telemetry_train_rows(
            settings.bootstrap_servers,
            settings.topic_telemetry,
            settings.window_seconds,
            train_devices,
            test_devices,
        )

    labeled = [r for r in rows if r.label in FAILURE_CLASSES]
    logger.info("train windows: %d (labeled %d)", len(rows), len(labeled))
    if len(labeled) < settings.min_train_windows:
        raise SystemExit(
            f"insufficient train windows: {len(labeled)} < {settings.min_train_windows}. "
            "Run reefer-pm-generate first."
        )

    pipe, meta = train_model(rows)
    save_model(pipe, settings.model_path, version=settings.model_version, extra=meta)
    logger.info("saved model %s (%s)", settings.model_path, meta)

    ensure_topics(settings.bootstrap_servers, [settings.topic_features])
    producer = create_producer(settings.bootstrap_servers)
    for row in rows:
        publish_json(
            producer,
            settings.topic_features,
            row.device_id,
            row.to_dict(),
        )
    producer.flush(30)
    logger.info("published %d feature rows to %s", len(rows), settings.topic_features)


if __name__ == "__main__":
    main()
