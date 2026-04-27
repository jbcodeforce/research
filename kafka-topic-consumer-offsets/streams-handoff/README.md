# Kafka Streams stop → read offsets → Flink SQL handoff

This folder documents a **local demo**: run the Java Kafka Streams pipeline in [`../kstream/`](../kstream/README.md), produce sample data with the Python CLI [`streams-demo-producer`](../pyproject.toml), **stop** Streams, **read committed offsets** for the Streams app on the **input** topic, then start **Flink SQL** with `scan.startup.mode` = `specific-offsets` so a new Flink consumer group continues from the same logical position on `streams-input`.

**Caveat:** This is an **offset handoff illustration**. Kafka Streams EOS and Flink checkpointing are different systems; you are not getting a production-grade “exactly-once” guarantee across the engine switch.

## What gets produced

| Piece | Role |
|--------|------|
| `uv run streams-demo-producer` | Publishes to `streams-input`. **Key** = `device-1` … `device-5` (UTF-8). **Value** = JSON `{"device_id":"...","value":"hello_<seq>"}` (e.g. `hello_100`). Use `--start-seq N` to continue numbering; `--follow` until interrupted. |
| `mvn exec:java` in `kstream/` | Reads the value as a string, writes `processed:` + `UPPER(value)` to `streams-output` (so the **whole JSON string** is uppercased on the output topic). |
| [`flink/continue_from_offsets.sql`](flink/continue_from_offsets.sql) | Declares a Kafka table on `streams-input` with `format` = `json`, a **new** `properties.group.id`, and `specific-offsets` you fill in from the steps below. Inserts to the **`print` connector** with `CONCAT('processed:', UPPER(value))` on the parsed `value` field. |

## Prerequisites

- broker running (e.g. [`../docker-compose.yaml`](../docker-compose.yaml) on `localhost:9092`)
- topics: `streams-input` and `streams-output` (see kstream README for `kafka-topics --create` commands)
- `uv` for Python; **Flink** with the **Kafka** SQL connector on the classpath (e.g. run SQL Client against a cluster; the [Iceberg quickstart stack](../../apache-iceberg-poc/README.md) in this repo uses Flink 2.x—verify connector options match your version)

## Steps

1. **Start the broker** (if needed):

   ```bash
   docker compose -f ../docker-compose.yaml up -d
   ```

2. **Create topics** (one partition is enough for the default SQL placeholder):

   ```bash
   docker compose -f ../docker-compose.yaml exec broker kafka-topics --bootstrap-server broker:29092 \
     --create --if-not-exists --topic streams-input --partitions 1 --replication-factor 1
   docker compose -f ../docker-compose.yaml exec broker kafka-topics --bootstrap-server broker:29092 \
     --create --if-not-exists --topic streams-output --partitions 1 --replication-factor 1
   ```

3. **Start Kafka Streams** (from `../kstream`):

   ```bash
   cd ../kstream
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   mvn -q exec:java
   ```

4. In another shell, **produce demo data** (from repo `kafka-topic-consumer-offsets/`):

   ```bash
   cd /path/to/kafka-topic-consumer-offsets
   uv sync
   export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
   uv run streams-demo-producer --local
   ```

5. (Optional) **Read the uppercased stream** on `streams-output` (see [`../kstream/README.md`](../kstream/README.md) for `kafka-console-consumer`).

6. **Stop Kafka Streams** with **Ctrl+C** in the `mvn exec:java` terminal so it can commit and exit cleanly.

7. **Read committed offsets** for the Streams app on **`streams-input`**. The Streams `application.id` defaults to **`kstream-eos-demo`**, which is the **consumer group id** for the application’s main consumer.

   From this folder’s parent:

   ```bash
   cd ..
   uv run topic-consumer-offsets --topic streams-input --show-all-groups
   ```

   Find rows for **`kstream-eos-demo`** and note **`committed=`** per **partition** (or use `kafka-consumer-groups --describe --group kstream-eos-demo` inside the broker container). Use the **partition** and **committed** offset that represents the **next** record to read for a new consumer (align with your broker/tool output; if a tool shows “log-end” vs “committed”, use the committed position for the group on `streams-input`).

8. **Edit** [`flink/continue_from_offsets.sql`](flink/continue_from_offsets.sql):

   - Set `properties.bootstrap.servers` to your broker (e.g. `localhost:9092`).
   - Replace `<NEXT_OFFSET>` in `scan.startup.specific-offsets` with the value from step 7, e.g. for a single partition:  
     `'partition:0,offset:5'`
   - If you use more than one partition, extend the list:  
     `'partition:0,offset:5;partition:1,offset:3'`

9. **Run the SQL** in Flink SQL Client (or your environment), after ensuring the **Kafka** connector JAR is available. For connector option spelling, use the [Flink Kafka connector docs](https://nightlies.apache.org/flink/flink-docs-release-2.2/docs/connectors/table/kafka/) for your Flink version.

10. (Optional) Produce **more** messages with `streams-demo-producer` and confirm the print sink shows only **new** rows if your offsets were set to the end of what Streams had already processed.

## Files

| File | Purpose |
|------|---------|
| [`flink/continue_from_offsets.sql`](flink/continue_from_offsets.sql) | Flink SQL: Kafka source + `print` sink, `specific-offsets` placeholder |
| [`notes.md`](notes.md) | Working notes for this research folder |

## See also

- [`../kstream/README.md`](../kstream/README.md) — build/run Streams, console produce/consume
- [`../../apache-iceberg-poc/README.md`](../../apache-iceberg-poc/README.md) — Docker Flink 2.x if you need a local SQL session with jars pre-wired (Iceberg-focused; add or confirm Kafka connector as needed for your test)
