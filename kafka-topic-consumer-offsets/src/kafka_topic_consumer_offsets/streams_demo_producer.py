"""
Send demo records for five device_id keys: JSON value {"device_id","value"} on Kafka.

Matches the kstream string pipeline (key + value strings); the Streams app uppercases
the value string. Use with streams-handoff/ docs and Flink SQL continuation examples.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

from confluent_kafka import KafkaException, Producer

from kafka_topic_consumer_offsets.topic_consumer_offsets import _client_config, _load_dotenv_file

DEVICE_IDS = [f"device-{i}" for i in range(1, 6)]


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--topic",
        default="streams-input",
        help="Topic to produce to (default: streams-input).",
    )
    p.add_argument(
        "--bootstrap-servers",
        default="",
        help="Optional; else KAFKA_BOOTSTRAP_SERVERS from .env.",
    )
    p.add_argument(
        "--send-per-key",
        type=int,
        default=1,
        metavar="N",
        help="How many messages to send per device (default: 1).",
    )
    p.add_argument(
        "--sleep-ms",
        type=int,
        default=0,
        metavar="MS",
        help="Sleep this many ms after each message (default: 0).",
    )
    p.add_argument(
        "--local",
        action="store_true",
        help="Use PLAINTEXT and ignore Confluent API keys (or rely on localhost bootstrap).",
    )
    p.add_argument("--config-file", help="Optional extra client properties (KEY=VALUE).")
    return p.parse_args()


def _run() -> int:
    args = _parse_args()
    _load_dotenv_file()
    base = _client_config(
        args.bootstrap_servers or "",
        args.config_file,
        force_local_plaintext=args.local,
    )
    if base is None:
        return 2

    conf: dict[str, Any] = dict(base)
    # Producer-friendly defaults; let broker decide acks
    p = Producer(conf)

    err_count = [0]

    def _delivery(err: object, msg: object) -> None:
        if err is not None:
            err_count[0] += 1
            print(f"Delivery failed: {err}", file=sys.stderr)
        else:
            assert msg is not None
            m = msg
            print(
                f"OK {m.topic()} p{m.partition()} @{m.offset()}",
                flush=True,
            )

    n = 0
    for _round in range(args.send_per_key):
        for i, did in enumerate(DEVICE_IDS, start=1):
            n += 1
            value_obj = {
                "device_id": did,
                "value": f"hello-{i}-r{_round + 1}",
            }
            payload = json.dumps(value_obj, separators=(",", ":")).encode("utf-8")
            key = did.encode("utf-8")
            try:
                p.produce(
                    args.topic,
                    key=key,
                    value=payload,
                    on_delivery=_delivery,
                )
                p.poll(0)
            except BufferError:
                p.poll(1.0)
                p.produce(
                    args.topic,
                    key=key,
                    value=payload,
                    on_delivery=_delivery,
                )
                p.poll(0)
            if args.sleep_ms:
                time.sleep(args.sleep_ms / 1000.0)

    unflushed = 1
    while unflushed:
        unflushed = p.flush(timeout=30.0)

    if err_count[0]:
        return 1
    print(
        f"Produced {n} message(s) to {args.topic!r} "
        f"({len(DEVICE_IDS)} device_id keys, {args.send_per_key} per key).",
        file=sys.stderr,
    )
    return 0


def main() -> None:
    try:
        raise SystemExit(_run())
    except KafkaException as e:
        print(f"Kafka error: {e}", file=sys.stderr)
        raise SystemExit(1) from e


if __name__ == "__main__":
    main()
