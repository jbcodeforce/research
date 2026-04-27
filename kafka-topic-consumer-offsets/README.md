# Research: Kafka consumer groups per topic & committed offsets (Python)

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

## Project layout (uv)

- **`pyproject.toml`** — project metadata and dependencies (no `requirements.txt`).
- **`src/kafka_topic_consumer_offsets/`** — package; CLI entry point is declared for `uv run`.
- **`uv.lock`** — lockfile; commit it so CI and teammates resolve the same versions.

**Setup and run** (from this directory):

```bash
uv sync
uv run topic-consumer-offsets --help
# or: uv run python -m kafka_topic_consumer_offsets.topic_consumer_offsets --help
```

**Add a dependency** later: `uv add <package>`, then commit the updated `pyproject.toml` and `uv.lock`.

### Confluent Cloud and `.env`

1. Copy `.env.example` to `.env` in this directory (`.env` is gitignored).
2. Set `KAFKA_BOOTSTRAP_SERVERS` to your cluster’s bootstrap (Kafka endpoint, e.g. `...confluent.cloud:9092`).
3. Set `KAFKA_API_KEY` and `KAFKA_API_SECRET` (or `KAFKA_API_SECRETS` as an alias for the secret) from the Confluent Cloud **API key** in the console.

**Auth note:** the Kafka client does **not** use an HTTP `Authorization: Bearer …` token. Confluent Cloud’s default cluster access uses **SASL_SSL** with **PLAIN**, where the API key is the SASL *username* and the secret is the SASL *password*. The script configures that when both key and secret are present. Leave them unset to talk to a local cluster with plain `PLAINTEXT` and `--bootstrap-servers` only.

With `.env` loaded, `--bootstrap-servers` is optional; you still must pass `--topic`.

**Example:**

```bash
uv sync
cp .env.example .env   # then edit with your cluster values

uv run topic-consumer-offsets \
  --bootstrap-servers localhost:9092 \
  --topic my-topic

# Include groups that have partition assignment but maybe no commits yet:
uv run topic-consumer-offsets \
  --bootstrap-servers localhost:9092 \
  --topic my-topic \
  --assignment

# Print every scanned group’s offsets, including OFFSET_INVALID (-1001) rows:
uv run topic-consumer-offsets \
  --bootstrap-servers localhost:9092 \
  --topic my-topic \
  --show-all-groups

# Transactional “stable” offsets:
uv run topic-consumer-offsets \
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
