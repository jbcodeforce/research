# Notes — Kafka topic consumer groups & committed offsets

## Goal

Python sample: given a topic name, find relevant consumer groups and print **read-committed** (stored) offsets per partition using the Kafka Admin API.

## Findings

- **No broker API** returns “all groups consuming topic X” directly. Practical approaches:
  1. **Committed offsets**: Enumerate `list_consumer_groups`, then for each group call `list_consumer_group_offsets` with `TopicPartition(topic, p)` for every partition. Groups with at least one partition where offset ≠ `OFFSET_INVALID` (-1001) have committed positions for that topic (or did).
  2. **Active assignment**: `describe_consumer_groups` and inspect member `assignment` for the topic — catches consumers that have not committed yet (optional, heavier).

- **confluent-kafka-python**: `ConsumerGroupTopicPartitions` lives in `confluent_kafka._model` but is also exposed as `confluent_kafka.ConsumerGroupTopicPartitions`. Docstring on `list_consumer_group_offsets` notes older limitation “single group”; implementation builds a future per request element — we pass **one group per call** for broad compatibility.

- **Stable offsets**: Kafka supports `require_stable=True` on `list_consumer_group_offsets` for transactional consumers (only completed transactions). Exposed as kwargs on the AdminClient method.

## What we built

- `topic_consumer_offsets.py`: CLI with `--bootstrap-servers`, `--topic`, optional `--show-all-groups` (include groups with no commits), `--require-stable`, `--assignment` (union groups discovered via describe assignment).

## Commands tried

- Verified imports and `AdminClient` / `describe_topics` / `list_consumer_group_offsets` against installed `confluent-kafka` on this machine.
- `python3 -m py_compile topic_consumer_offsets.py` and `--help` OK.

## Follow-ups (optional)

- For huge clusters, replace full group scan with a maintained registry or broker-side metrics if available.
- Compare with `kafka-consumer-groups.sh --describe` output for one group to validate offsets match expectations.
