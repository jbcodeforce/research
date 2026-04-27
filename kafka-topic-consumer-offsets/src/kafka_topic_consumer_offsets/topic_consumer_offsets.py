#!/usr/bin/env python3
"""
List consumer groups relevant to a topic and print committed offsets per partition.

Kafka does not expose "groups by topic" in one call. This script:
  1) Loads partition IDs for the topic (describe_topics).
  2) Lists all consumer groups (list_consumer_groups).
  3) For each group, fetches list_consumer_group_offsets for that topic's partitions.
  4) Optionally describes groups and includes those with partition assignment for the topic
     even when no offset is committed yet (--assignment).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Iterable

from confluent_kafka import ConsumerGroupTopicPartitions, TopicCollection, TopicPartition
from confluent_kafka.admin import OFFSET_INVALID, AdminClient, KafkaException

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover
    load_dotenv = None  # type: ignore[assignment, misc]


def _project_root() -> Path:
    """Project root (contains pyproject.toml and .env), not the package under src/."""
    return Path(__file__).resolve().parents[2]


def _load_dotenv_file() -> None:
    if load_dotenv is None:
        return
    load_dotenv(_project_root() / ".env")
    load_dotenv()


def _client_config(
    bootstrap_servers: str,
    config_file: str | None,
) -> dict[str, str] | None:
    """Build AdminClient config; Confluent Cloud uses SASL_SSL + PLAIN (key/secret), not HTTP Bearer."""
    conf: dict[str, str] = {}
    bs = (bootstrap_servers or os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "")).strip()
    if not bs:
        print(
            "Set KAFKA_BOOTSTRAP_SERVERS in .env or pass --bootstrap-servers",
            file=sys.stderr,
        )
        return None
    conf["bootstrap.servers"] = bs

    key = (os.environ.get("KAFKA_API_KEY") or "").strip()
    secret = (
        os.environ.get("KAFKA_API_SECRET")
        or os.environ.get("KAFKA_API_SECRETS")
        or ""
    ).strip()
    if key and secret:
        conf["security.protocol"] = "SASL_SSL"
        conf["sasl.mechanisms"] = "PLAIN"
        conf["sasl.username"] = key
        conf["sasl.password"] = secret
    elif key or secret:
        print(
            "Set both KAFKA_API_KEY and KAFKA_API_SECRET (or KAFKA_API_SECRETS) for Confluent auth",
            file=sys.stderr,
        )
        return None

    if config_file:
        with open(config_file, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                conf[k.strip()] = v.strip()

    return conf


def _topic_partition_ids(admin: AdminClient, topic: str, timeout: float) -> list[int]:
    fs = admin.describe_topics(TopicCollection([topic]), request_timeout=timeout)
    fut = fs.get(topic)
    if fut is None:
        raise RuntimeError(f"describe_topics did not return future for {topic!r}")
    desc = fut.result()
    if desc is None:
        raise RuntimeError(f"No metadata for topic {topic!r}")
    return sorted(p.id for p in desc.partitions)


def _list_all_group_ids(admin: AdminClient, timeout: float) -> list[str]:
    fut = admin.list_consumer_groups(request_timeout=timeout)
    result = fut.result()
    return [g.group_id for g in result.valid]


def _offsets_for_group(
    admin: AdminClient,
    group_id: str,
    topic: str,
    partition_ids: Iterable[int],
    timeout: float,
    require_stable: bool,
) -> ConsumerGroupTopicPartitions:
    tps = [TopicPartition(topic, p) for p in partition_ids]
    req = [ConsumerGroupTopicPartitions(group_id, tps)]
    kwargs: dict[str, Any] = {"request_timeout": timeout}
    if require_stable:
        kwargs["require_stable"] = True
    futmap = admin.list_consumer_group_offsets(req, **kwargs)
    return futmap[group_id].result()


def _group_ids_with_assignment(
    admin: AdminClient,
    topic: str,
    group_ids: list[str],
    timeout: float,
    describe_batch: int,
) -> set[str]:
    """Groups where at least one member has an assigned partition for ``topic``."""
    found: set[str] = set()
    for i in range(0, len(group_ids), describe_batch):
        batch = group_ids[i : i + describe_batch]
        fs = admin.describe_consumer_groups(batch, request_timeout=timeout)
        for gid, fut in fs.items():
            try:
                desc = fut.result()
            except KafkaException:
                continue
            for m in desc.members:
                assign = m.assignment
                if assign is None:
                    continue
                for tp in assign.topic_partitions:
                    if tp.topic == topic:
                        found.add(gid)
                        break
    return found


def _run(args: argparse.Namespace) -> int:
    conf = _client_config(
        args.bootstrap_servers or "",
        args.config_file,
    )
    if conf is None:
        return 2

    admin = AdminClient(conf)
    timeout = args.timeout

    try:
        partition_ids = _topic_partition_ids(admin, args.topic, timeout)
    except KafkaException as e:
        print(f"describe_topics failed: {e}", file=sys.stderr)
        return 1

    if not partition_ids:
        print(f"Topic {args.topic!r} has no partitions (or metadata empty).", file=sys.stderr)
        return 1

    try:
        group_ids = _list_all_group_ids(admin, timeout)
    except KafkaException as e:
        print(f"list_consumer_groups failed: {e}", file=sys.stderr)
        return 1

    assignment_groups: set[str] = set()
    if args.assignment:
        assignment_groups = _group_ids_with_assignment(
            admin, args.topic, group_ids, timeout, args.describe_batch
        )

    rows: list[dict[str, Any]] = []
    offset_errors: list[dict[str, Any]] = []

    def fetch_one(gid: str) -> tuple[str, ConsumerGroupTopicPartitions | Exception]:
        try:
            res = _offsets_for_group(
                admin,
                gid,
                args.topic,
                partition_ids,
                timeout,
                args.require_stable,
            )
            return gid, res
        except Exception as e:  # noqa: BLE001 — surface per-group errors
            return gid, e

    workers = min(args.max_workers, max(1, len(group_ids)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fetch_one, gid): gid for gid in group_ids}
        for fut in as_completed(futs):
            gid, payload = fut.result()
            if isinstance(payload, Exception):
                offset_errors.append({"group_id": gid, "error": repr(payload)})
                continue
            for tp in payload.topic_partitions:
                off = tp.offset
                meta = getattr(tp, "metadata", None)
                rows.append(
                    {
                        "group_id": gid,
                        "topic": tp.topic,
                        "partition": tp.partition,
                        "committed_offset": None if off == OFFSET_INVALID else off,
                        "offset_invalid": off == OFFSET_INVALID,
                        "metadata": meta,
                    }
                )

    groups_with_commit = {
        r["group_id"]
        for r in rows
        if not r.get("offset_invalid") and r.get("committed_offset") is not None
    }
    groups_with_offset_response = {r["group_id"] for r in rows}

    if args.show_all_groups:
        eligible = set(group_ids)
    elif args.assignment:
        eligible = groups_with_commit | assignment_groups
    else:
        eligible = groups_with_commit

    rows = [r for r in rows if r["group_id"] in eligible]

    if args.assignment:
        for gid in assignment_groups:
            if gid not in eligible:
                continue
            if gid in groups_with_offset_response:
                continue
            for p in partition_ids:
                rows.append(
                    {
                        "group_id": gid,
                        "topic": args.topic,
                        "partition": p,
                        "committed_offset": None,
                        "offset_invalid": True,
                        "metadata": None,
                        "note": "assignment_only_offset_request_failed_or_empty",
                    }
                )

    if args.verbose:
        rows.extend({**e, "topic": args.topic} for e in offset_errors)

    rows.sort(key=lambda r: (r["group_id"], r.get("partition", -1)))

    if args.format == "json":
        print(json.dumps(rows, indent=2))
    else:
        print(f"topic={args.topic} partitions={partition_ids} groups_scanned={len(group_ids)}")
        for r in rows:
            if "error" in r:
                print(f"{r['group_id']}\tERROR\t{r['error']}")
                continue
            co = r.get("committed_offset")
            inv = r.get("offset_invalid")
            extra = f"\t{r.get('note')}" if r.get("note") else ""
            print(
                f"{r['group_id']}\tp{r['partition']}\t"
                f"committed={co}\tinvalid={inv}\tmeta={r.get('metadata')}{extra}"
            )

    return 0


def main() -> None:
    _load_dotenv_file()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--bootstrap-servers",
        default="",
        help="Broker list; if omitted, KAFKA_BOOTSTRAP_SERVERS from .env is used",
    )
    p.add_argument("--topic", required=True)
    p.add_argument("--timeout", type=float, default=30.0)
    p.add_argument("--require-stable", action="store_true", help="Transactional stable offsets")
    p.add_argument(
        "--show-all-groups",
        action="store_true",
        help="Print every group's partitions even when offset is OFFSET_INVALID",
    )
    p.add_argument(
        "--assignment",
        action="store_true",
        help="Also discover groups with active assignment for the topic (describe_consumer_groups)",
    )
    p.add_argument("--describe-batch", type=int, default=40, help="Batch size for describe_consumer_groups")
    p.add_argument("--max-workers", type=int, default=16, help="Parallel offset lookups")
    p.add_argument("--format", choices=("text", "json"), default="text")
    p.add_argument("--verbose", action="store_true", help="Log per-group offset errors into output")
    p.add_argument("--config-file", help="Optional client properties file (KEY=VALUE lines)")
    args = p.parse_args()
    raise SystemExit(_run(args))


if __name__ == "__main__":
    main()
