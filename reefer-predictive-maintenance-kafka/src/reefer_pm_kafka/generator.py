"""Synthetic reefer telemetry with embedded failure physics."""

from __future__ import annotations

import argparse
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

import numpy as np

from reefer_pm_kafka.config import FAILURE_CLASSES, GeneratorConfig, load_generator_config, load_settings
from reefer_pm_kafka.kafka_utils import create_producer, ensure_topics
from reefer_pm_kafka.schema import new_event_id, validate_telemetry

logger = logging.getLogger(__name__)


def _failure_class_for_progress(progress: float) -> str:
    """Map normalized timeline progress to failure class."""
    if progress < 0.55:
        return "healthy"
    if progress < 0.82:
        return "degraded"
    return "failure_imminent"


def _telemetry_values(
    failure_class: str,
    rng: np.random.Generator,
    compressor_hours: float,
) -> dict[str, float | int]:
    """Produce sensor readings that reflect the failure class."""
    if failure_class == "healthy":
        return_air = float(rng.uniform(1.0, 5.0))
        supply_air = float(rng.uniform(-2.0, 3.0))
        power = float(rng.uniform(5.0, 7.5))
        vibration = float(rng.uniform(0.08, 0.25))
        doors = int(rng.integers(0, 2))
    elif failure_class == "degraded":
        return_air = float(rng.uniform(6.0, 10.0))
        supply_air = float(rng.uniform(2.0, 5.0))
        power = float(rng.uniform(8.5, 11.0))
        vibration = float(rng.uniform(0.35, 0.65))
        doors = int(rng.integers(1, 4))
    else:
        return_air = float(rng.uniform(12.0, 18.0))
        supply_air = float(rng.uniform(4.0, 8.0))
        power = float(rng.uniform(12.0, 16.0))
        vibration = float(rng.uniform(0.8, 1.4))
        doors = int(rng.integers(3, 8))

    return {
        "return_air_temp_c": return_air,
        "supply_air_temp_c": supply_air,
        "compressor_runtime_h": compressor_hours,
        "door_open_count": doors,
        "power_draw_kw": power,
        "vibration_rms": vibration,
    }


def generate_records(
    cfg: GeneratorConfig,
    *,
    base_time: datetime | None = None,
) -> Iterator[dict[str, Any]]:
    """Yield train, test, then inference records (interleaved per phase)."""
    rng = np.random.default_rng(cfg.random_seed)
    start = base_time or datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    global_offset = 0

    phases: list[tuple[str, list[str], bool]] = [
        ("train", cfg.train_devices, True),
        ("test", cfg.test_devices, True),
        ("inference", cfg.inference_devices, False),
    ]

    for split, devices, is_labeled in phases:
        count = cfg.events_per_device[split]
        for device in devices:
            compressor_hours = float(rng.uniform(1000, 5000))
            for i in range(count):
                progress = i / max(count - 1, 1)
                failure_class = _failure_class_for_progress(progress) if is_labeled else None
                ts = start + timedelta(
                    seconds=global_offset * cfg.event_interval_seconds,
                )
                global_offset += 1
                compressor_hours += cfg.event_interval_seconds / 3600.0

                sensors = _telemetry_values(
                    failure_class or "healthy",
                    rng,
                    compressor_hours,
                )
                record: dict[str, Any] = {
                    "event_id": new_event_id(),
                    "device_id": device,
                    "event_time": ts.isoformat().replace("+00:00", "Z"),
                    **sensors,
                    "meta": {"split": split, "is_labeled": is_labeled},
                    "label": {
                        "failure_class": failure_class,
                        "horizon_hours": 24 if is_labeled else None,
                    },
                }
                errors = validate_telemetry(record)
                if errors:
                    raise ValueError(f"invalid generated record: {errors}")
                yield record


def publish_records(
    records: list[dict[str, Any]],
    *,
    bootstrap_servers: str,
    topic: str,
) -> int:
    """Publish telemetry JSON to Kafka; return count sent."""
    producer = create_producer(bootstrap_servers)
    sent = 0
    try:
        for rec in records:
            producer.produce(
                topic,
                key=rec["device_id"].encode("utf-8"),
                value=json.dumps(rec).encode("utf-8"),
            )
            sent += 1
        producer.flush(30)
    finally:
        producer.flush(5)
    return sent


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="Publish synthetic reefer telemetry")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print record counts only; do not publish",
    )
    args = parser.parse_args()

    settings = load_settings()
    cfg = load_generator_config()
    records = list(generate_records(cfg))
    splits = {s: sum(1 for r in records if r["meta"]["split"] == s) for s in ("train", "test", "inference")}
    logger.info("generated %d records: %s", len(records), splits)

    if args.dry_run:
        return

    ensure_topics(
        settings.bootstrap_servers,
        [
            settings.topic_telemetry,
            settings.topic_features,
            settings.topic_predictions,
            settings.topic_metrics,
        ],
    )
    n = publish_records(
        records,
        bootstrap_servers=settings.bootstrap_servers,
        topic=settings.topic_telemetry,
    )
    logger.info("published %d records to %s", n, settings.topic_telemetry)


if __name__ == "__main__":
    main()
