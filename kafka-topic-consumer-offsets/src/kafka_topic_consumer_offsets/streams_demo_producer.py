"""
Send demo records for five device_id keys: JSON value {"device_id","value"} on Kafka.

Value text is hello_<seq> (e.g. hello_1, hello_100) with a global sequence incremented
per message. Use --start-seq to resume (e.g. --start-seq 100) and --follow to run until
Ctrl+C. Matches the kstream string pipeline; the Streams app uppercases the value.
"""

from __future__ import annotations

import argparse
import json
import signal
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
        help="Rounds: each round sends one message per device. Ignored with --follow (default: 1).",
    )
    p.add_argument(
        "--start-seq",
        type=int,
        default=1,
        metavar="N",
        help="First message value uses hello_<N> (underscore); each message increments by 1 (default: 1).",
    )
    p.add_argument(
        "--follow",
        action="store_true",
        help="Run until SIGINT/SIGTERM: round-robin all devices, incrementing the sequence; ignores --send-per-key.",
    )
    p.add_argument(
        "--sleep-ms",
        type=int,
        default=100,
        metavar="MS",
        help="Sleep this many ms after each message (default:100).",
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

    stop = [False]

    def _on_signal(_signum: int, _frame: object) -> None:
        stop[0] = True

    if args.follow:
        signal.signal(signal.SIGINT, _on_signal)
        signal.signal(signal.SIGTERM, _on_signal)
        if args.send_per_key != 1:
            print(
                "--follow: ignoring --send-per-key (infinite run until signal).",
                file=sys.stderr,
            )

    def _emit_one(did: str, seq: int) -> None:
        value_obj = {
            "device_id": did,
            "value": f"hello_{seq}",
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

    n = 0
    seq = args.start_seq
    try:
        if args.follow:
            while not stop[0]:
                for did in DEVICE_IDS:
                    if stop[0]:
                        break
                    n += 1
                    _emit_one(did, seq)
                    seq += 1
        else:
            for _round in range(args.send_per_key):
                for did in DEVICE_IDS:
                    n += 1
                    _emit_one(did, seq)
                    seq += 1
    finally:
        unflushed: int = 1
        while unflushed:
            unflushed = p.flush(timeout=30.0)

    if err_count[0]:
        return 1
    if args.follow:
        print(
            f"Stopped after {n} message(s) to {args.topic!r} "
            f"(next value sequence would be hello_{seq}).",
            file=sys.stderr,
        )
    else:
        print(
            f"Produced {n} message(s) to {args.topic!r} "
            f"({len(DEVICE_IDS)} device_id keys, {args.send_per_key} round(s); "
            f"values hello_{args.start_seq}..hello_{seq - 1}).",
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
