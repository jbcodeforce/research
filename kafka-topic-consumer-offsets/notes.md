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

- **uv project:** `pyproject.toml` + `uv.lock`, `src/kafka_topic_consumer_offsets/`; console script `topic-consumer-offsets` → `main`.
- **CLI** (`topic_consumer_offsets.py` module): `--bootstrap-servers`, `--topic`, optional `--show-all-groups`, `--require-stable`, `--assignment` (union groups from describe).
- **Confluent Cloud / `.env`:** load `.env` from **project root** (parent of `src/`); `KAFKA_BOOTSTRAP_SERVERS`, `KAFKA_API_KEY`, `KAFKA_API_SECRET` (or `KAFKA_API_SECRETS`) → `SASL_SSL` + `PLAIN` (not HTTP Bearer).
- `.env.example` committed; `.env` gitignored (user copies and fills).
- **`docker-compose.yaml`:** Confluent `cp-kafka:8.2.0` in **KRaft** mode (combined broker+controller, `CLUSTER_ID` + `KAFKA_LOG_DIRS`); host `localhost:9092` for the CLI, internal `broker:29092` for `docker compose exec` tools.

## Commands tried

- `uv lock`, `uv sync`, `uv run topic-consumer-offsets --help`.
- **confluent-kafka ≥2.14:** `AdminClient.describe_topics` takes `TopicCollection([...])`, not a raw list of names.
- **`demo_consumer.py` / `uv run demo-kafka-consumer`:** minimal `Consumer` with `enable.auto.commit` + subscribe; same env as the offset CLI; demonstrates a visible group with committed read offsets.
- **Local vs Confluent in `.env`:** if bootstrap hosts are all local (see `_bootstrap_is_local_only` / `host.docker.internal`), `_client_config` uses **PLAINTEXT** and skips API keys; optional **`--local`** forces PLAINTEXT when bootstrap is a non-local IP.
- **`kstream/`:** Java `KafkaStreams` with `EXACTLY_ONCE_V2` (see `kstream/README.md`); `application.id` default `kstream-eos-demo`; Apache Kafka 3.8.0 for CP 8.2 alignment; **Maven** (`pom.xml`, `mvn exec:java`).
- Earlier: `confluent-kafka` AdminClient smoke checks.

## Follow-ups (optional)

- For huge clusters, replace full group scan with a maintained registry or broker-side metrics if available.
- Compare with `kafka-consumer-groups.sh --describe` output for one group to validate offsets match expectations.
