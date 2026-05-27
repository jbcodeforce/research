"""Publish NDJSON Debezium fixtures to Kafka topics keyed by transaction.id."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from confluent_kafka import Producer
from dotenv import load_dotenv

DEFAULT_ORDERS_TOPIC = "mt.public.orders"
DEFAULT_ITEMS_TOPIC = "mt.public.order_items"
DEFAULT_TX_TOPIC = "mt.transaction"


def _load_ndjson(path: Path) -> list[dict]:
    """Load newline-delimited JSON objects from a file."""
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            records.append(json.loads(line))
    return records


def _tx_key(record: dict) -> str | None:
    """Extract Kafka key from Debezium transaction metadata."""
    tx = record.get("transaction")
    if isinstance(tx, dict) and tx.get("id"):
        return str(tx["id"])
    if record.get("id"):
        return str(record["id"])
    return None


def _delivery_report(err, msg) -> None:
    if err is not None:
        print(f"Delivery failed: {err}", file=sys.stderr)


def produce_file(
    producer: Producer,
    topic: str,
    path: Path,
    *,
    use_tx_key: bool,
) -> int:
    """Produce all records from an NDJSON file; return count sent."""
    count = 0
    for record in _load_ndjson(path):
        key = _tx_key(record) if use_tx_key else None
        payload = json.dumps(record).encode("utf-8")
        producer.produce(
            topic,
            key=key.encode("utf-8") if key else None,
            value=payload,
            callback=_delivery_report,
        )
        count += 1
    producer.flush()
    return count


def build_producer() -> Producer:
    """Build Kafka producer from environment variables."""
    bootstrap = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "127.0.0.1:9092")
    conf: dict[str, str] = {"bootstrap.servers": bootstrap}
    if os.environ.get("KAFKA_SECURITY_PROTOCOL"):
        conf["security.protocol"] = os.environ["KAFKA_SECURITY_PROTOCOL"]
    if os.environ.get("KAFKA_SASL_MECHANISM"):
        conf["sasl.mechanisms"] = os.environ["KAFKA_SASL_MECHANISM"]
    if os.environ.get("KAFKA_SASL_USERNAME"):
        conf["sasl.username"] = os.environ["KAFKA_SASL_USERNAME"]
    if os.environ.get("KAFKA_SASL_PASSWORD"):
        conf["sasl.password"] = os.environ["KAFKA_SASL_PASSWORD"]
    return Producer(conf)


def main() -> None:
    """CLI entry: publish test-data/debezium NDJSON to Kafka topics."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Publish mock Debezium CDC to Kafka")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path(__file__).resolve().parents[2] / "test-data" / "debezium",
        help="Directory with orders.json, order_items.json, transaction.json",
    )
    parser.add_argument("--orders-topic", default=DEFAULT_ORDERS_TOPIC)
    parser.add_argument("--items-topic", default=DEFAULT_ITEMS_TOPIC)
    parser.add_argument("--transaction-topic", default=DEFAULT_TX_TOPIC)
    args = parser.parse_args()

    data_dir: Path = args.data_dir
    producer = build_producer()

    n_orders = produce_file(
        producer, args.orders_topic, data_dir / "orders.json", use_tx_key=True
    )
    n_items = produce_file(
        producer, args.items_topic, data_dir / "order_items.json", use_tx_key=True
    )
    n_tx = produce_file(
        producer, args.transaction_topic, data_dir / "transaction.json", use_tx_key=True
    )
    print(
        f"Produced {n_orders} orders, {n_items} order_items, {n_tx} transaction events "
        f"to {args.orders_topic}, {args.items_topic}, {args.transaction_topic}"
    )


if __name__ == "__main__":
    main()
