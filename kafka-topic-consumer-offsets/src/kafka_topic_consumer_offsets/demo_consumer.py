"""
Minimal consumer to illustrate a visible group with committed offsets.

Run this, then `uv run topic-consumer-offsets --topic <same> --show-all-groups`
to see the group and per-partition committed offsets.
"""

from __future__ import annotations

import argparse
import signal
import sys
import time
from typing import Any

from confluent_kafka import Consumer, KafkaError, KafkaException, Message

from kafka_topic_consumer_offsets.topic_consumer_offsets import _client_config, _load_dotenv_file


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--topic",
        required=True,
        help="Topic to subscribe to (same as you pass to topic-consumer-offsets).",
    )
    p.add_argument(
        "--group",
        default="demo-committed-offsets",
        help="Consumer group id (visible in list_consumer_group_offsets).",
    )
    p.add_argument(
        "--bootstrap-servers",
        default="",
        help="Optional; else KAFKA_BOOTSTRAP_SERVERS from .env.",
    )
    p.add_argument(
        "--max-messages",
        type=int,
        default=5,
        help="Stop after this many successful messages (default: 5).",
    )
    p.add_argument(
        "--max-wait-seconds",
        type=float,
        default=60.0,
        help="Stop after this long if not enough messages (default: 60).",
    )
    p.add_argument(
        "--auto-commit-interval-ms",
        type=int,
        default=1000,
        help="How often the client may commit offsets in the background (default: 1000).",
    )
    p.add_argument("--config-file", help="Optional extra client properties (KEY=VALUE).")
    return p.parse_args()


def _run() -> int:
    args = _parse_args()
    _load_dotenv_file()
    base = _client_config(args.bootstrap_servers or "", args.config_file)
    if base is None:
        return 2

    conf: dict[str, Any] = dict(base)
    conf.update(
        {
            "group.id": args.group,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": True,
            "auto.commit.interval.ms": args.auto_commit_interval_ms,
            "session.timeout.ms": 45000,
        }
    )

    stop = False

    def _handle(_sig: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, _handle)
    signal.signal(signal.SIGTERM, _handle)

    print(
        f"Subscribing: topic={args.topic!r} group={args.group!r} — "
        f"will read up to {args.max_messages} message(s) then close (commits on exit).",
        file=sys.stderr,
    )

    consumer = Consumer(conf)
    consumer.subscribe([args.topic])
    n = 0
    t0 = time.monotonic()
    try:
        while n < args.max_messages and not stop:
            if time.monotonic() - t0 > args.max_wait_seconds:
                print("Timed out waiting for messages.", file=sys.stderr)
                return 1
            msg: Message | None = consumer.poll(timeout=1.0)
            if msg is None:
                continue
            if msg.error():
                err = msg.error()
                if err.code() == KafkaError._PARTITION_EOF:
                    continue
                raise KafkaException(err)
            n += 1
            key = msg.key()
            val = msg.value()
            line = f"[{n}] {msg.topic()} p{msg.partition()} @{msg.offset()}"
            if val is not None:
                line += f" value_len={len(val)}"
            if key is not None:
                line += f" key_len={len(key)}"
            print(line, flush=True)
    finally:
        # Close commits offsets for this consumer (with auto commit, prior commits may have run)
        consumer.close()
        print(
            f"Consumer closed. Group {args.group!r} should have committed read offsets. "
            f"Run: uv run topic-consumer-offsets --topic {args.topic!r} --show-all-groups",
            file=sys.stderr,
        )
    return 0 if n > 0 or stop else 1


def main() -> None:
    raise SystemExit(_run())


if __name__ == "__main__":
    main()
