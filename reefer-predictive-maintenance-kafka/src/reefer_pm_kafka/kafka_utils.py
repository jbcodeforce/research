"""Kafka admin, producer, and consumer helpers."""

from __future__ import annotations

import json
import logging
from typing import Any

from confluent_kafka import Consumer, Producer
from confluent_kafka.admin import AdminClient, NewTopic

logger = logging.getLogger(__name__)

POLL_IDLE_SECONDS = 3.0


def normalize_bootstrap_servers(bootstrap_servers: str) -> str:
    """Use IPv4 for localhost — librdkafka often tries [::1] first and fails on Docker."""
    parts = []
    for entry in bootstrap_servers.split(","):
        entry = entry.strip()
        host, sep, port = entry.rpartition(":")
        if host in ("localhost", "::1", "[::1]"):
            host = "127.0.0.1"
        parts.append(f"{host}{sep}{port}" if sep else host)
    return ",".join(parts)


def _client_config(bootstrap_servers: str) -> dict[str, str]:
    return {
        "bootstrap.servers": normalize_bootstrap_servers(bootstrap_servers),
        # Avoid [::1] when broker metadata advertises localhost (common on macOS + Docker).
        "broker.address.family": "v4",
    }


def create_producer(bootstrap_servers: str) -> Producer:
    return Producer(_client_config(bootstrap_servers))


def create_consumer(
    bootstrap_servers: str,
    group_id: str,
    *,
    topics: list[str],
) -> Consumer:
    consumer = Consumer(
        {
            **_client_config(bootstrap_servers),
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
        }
    )
    consumer.subscribe(topics)
    return consumer


def ensure_topics(bootstrap_servers: str, topic_names: list[str], *, partitions: int = 3) -> None:
    """Create topics if they do not exist."""
    admin = AdminClient(_client_config(bootstrap_servers))
    metadata = admin.list_topics(timeout=10)
    existing = set(metadata.topics.keys())
    to_create = [
        NewTopic(name, num_partitions=partitions, replication_factor=1)
        for name in topic_names
        if name not in existing
    ]
    if not to_create:
        return
    futures = admin.create_topics(to_create)
    for topic, future in futures.items():
        try:
            future.result()
            logger.info("created topic %s", topic)
        except Exception as exc:
            if "already exists" in str(exc).lower():
                logger.info("topic %s already exists", topic)
            else:
                raise


def consume_all_json(
    bootstrap_servers: str,
    topic: str,
    group_id: str,
    *,
    idle_timeout: float = POLL_IDLE_SECONDS,
) -> list[dict[str, Any]]:
    """Read all available messages until idle timeout (batch demo mode)."""
    consumer = create_consumer(bootstrap_servers, group_id, topics=[topic])
    records: list[dict[str, Any]] = []
    try:
        idle_polls = 0
        max_idle_polls = int(idle_timeout / 0.5) + 1
        while idle_polls < max_idle_polls:
            msg = consumer.poll(0.5)
            if msg is None:
                idle_polls += 1
                continue
            idle_polls = 0
            if msg.error():
                logger.warning("consumer error: %s", msg.error())
                continue
            payload = json.loads(msg.value().decode("utf-8"))
            records.append(payload)
    finally:
        consumer.close()
    return records


def publish_json(
    producer: Producer,
    topic: str,
    key: str,
    payload: dict[str, Any],
) -> None:
    producer.produce(
        topic,
        key=key.encode("utf-8"),
        value=json.dumps(payload).encode("utf-8"),
    )


def create_topics_main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    from reefer_pm_kafka.config import load_settings

    settings = load_settings()
    ensure_topics(
        settings.bootstrap_servers,
        [
            settings.topic_telemetry,
            settings.topic_features,
            settings.topic_predictions,
            settings.topic_metrics,
        ],
    )
    logger.info("topics ready on %s", settings.bootstrap_servers)
