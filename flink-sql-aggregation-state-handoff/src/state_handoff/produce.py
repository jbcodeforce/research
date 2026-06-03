"""Build keyed device events for the handoff demo."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from dotenv import load_dotenv


def device_id_for_index(index: int, num_keys: int) -> str:
    """Return a stable device_id cycling through device-1 .. device-N."""
    if num_keys < 1:
        raise ValueError("num_keys must be >= 1")
    return f"device-{(index % num_keys) + 1}"


def build_event(seq: int, num_keys: int, base_amount: int) -> dict:
    """Build one JSON event with monotonic seq and deterministic amount."""
    return {
        "device_id": device_id_for_index(seq, num_keys),
        "amount": base_amount + seq,
        "event_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
        "seq": seq,
    }


def event_payload(event: dict) -> bytes:
    """Serialize an event dict to UTF-8 JSON bytes for Kafka."""
    return json.dumps(event, separators=(",", ":")).encode("utf-8")


def _kafka_producer():
    from confluent_kafka import Producer

    bootstrap = os.environ["BOOTSTRAP_SERVERS"]
    conf = {
        "bootstrap.servers": bootstrap,
        "security.protocol": "SASL_SSL",
        "sasl.mechanism": "PLAIN",
        "sasl.username": os.environ["KAFKA_API_KEY"],
        "sasl.password": os.environ["KAFKA_API_SECRET"],
    }
    return Producer(conf)


def produce_events(
    count: int,
    num_keys: int,
    base_amount: int,
    topic: str,
    start_seq: int = 0,
) -> list[dict]:
    """Produce count events to Kafka and return the emitted event dicts."""
    producer = _kafka_producer()
    emitted: list[dict] = []
    for i in range(count):
        seq = start_seq + i
        event = build_event(seq, num_keys, base_amount)
        producer.produce(
            topic,
            key=event["device_id"].encode("utf-8"),
            value=event_payload(event),
        )
        emitted.append(event)
    producer.flush()
    return emitted


def main() -> None:
    """CLI entry: produce demo events to device-events topic."""
    load_dotenv()
    parser = argparse.ArgumentParser(description="Produce keyed device events for handoff demo")
    parser.add_argument("--count", type=int, default=100, help="Number of events to produce")
    parser.add_argument("--keys", type=int, default=5, help="Number of distinct device keys")
    parser.add_argument("--base-amount", type=int, default=10, help="Base amount added to seq")
    parser.add_argument("--start-seq", type=int, default=0, help="Starting sequence number")
    parser.add_argument(
        "--topic",
        default=os.environ.get("SOURCE_TOPIC", "device-events"),
        help="Kafka source topic",
    )
    args = parser.parse_args()

    events = produce_events(
        count=args.count,
        num_keys=args.keys,
        base_amount=args.base_amount,
        topic=args.topic,
        start_seq=args.start_seq,
    )
    totals: dict[str, int] = {}
    for event in events:
        totals[event["device_id"]] = totals.get(event["device_id"], 0) + event["amount"]
    print(f"Produced {len(events)} events to {args.topic}")
    print("Per-key amounts this batch:", json.dumps(totals, sort_keys=True))


if __name__ == "__main__":
    main()
