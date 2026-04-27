# Research: Consumer groups per topic & committed offsets (Python)

## Problem

Given a Kafka **topic**, you often need:

1. Which **consumer groups** relate to that topic (not just every group in the cluster).
2. For each group, the **last committed (read-committed / stored) offset** per partition — the offsets consumers have committed to Kafka’s `__consumer_offsets` topic.

Kafka’s Admin API does **not** expose a single RPC such as “list consumer groups by topic”. You derive the answer by combining metadata and consumer-group APIs.

## Approaches

| Approach | Idea | Pros | Cons |
|----------|------|------|------|
| **Committed offsets** | Enumerate groups with `list_consumer_groups`. For each group, call `list_consumer_group_offsets` scoped to `(topic, partition)` for every partition of the topic. | Simple; matches “current committed offset” literally. | Misses consumers that have **joined** but never **committed** yet. |
| **Active assignment** | `describe_consumer_groups` and inspect member **assignment** for your topic. | Finds active readers without commits. | More broker load; larger responses. |

This folder’s script defaults to **committed offsets** and optionally adds **assignment** (`--assignment`) so you can union both views.

## Script: `topic_consumer_offsets.py`

**Dependencies:** see `requirements.txt` (`confluent-kafka`).

**Example:**

```bash
uv pip install -r requirements.txt   # or pip install -r requirements.txt

python topic_consumer_offsets.py \
  --bootstrap-servers localhost:9092 \
  --topic my-topic

# Include groups that have partition assignment but maybe no commits yet:
python topic_consumer_offsets.py \
  --bootstrap-servers localhost:9092 \
  --topic my-topic \
  --assignment

# Print every scanned group’s offsets, including OFFSET_INVALID (-1001) rows:
python topic_consumer_offsets.py \
  --bootstrap-servers localhost:9092 \
  --topic my-topic \
  --show-all-groups

# Transactional “stable” offsets:
python topic_consumer_offsets.py \
  --bootstrap-servers localhost:9092 \
  --topic my-topic \
  --require-stable
```

**Output (text):** one line per `(group, partition)` with `committed=` and `invalid=` (true when offset is `OFFSET_INVALID`).

**JSON:** `--format json` for machine-readable rows.

### ACLs

Listing groups and offsets typically needs `DESCRIBE` on the `GROUP` resource and relevant `CLUSTER`/`TOPIC` permissions. Adjust for your Kafka/Confluent Cloud security model.

## References

- Confluent Kafka Python Admin: `AdminClient.list_consumer_groups`, `list_consumer_group_offsets`, `describe_consumer_groups`, `describe_topics`.
- Internal notes: `notes.md`.
