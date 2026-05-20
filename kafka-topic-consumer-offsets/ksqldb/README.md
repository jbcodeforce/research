# ksqlDB — consume / process / produce (Confluent Cloud)

ksqlDB equivalent of the Java Kafka Streams sample in [`../kstream/`](../kstream/README.md):

- Read **String** keys and values from `streams-input`
- Parse JSON values with a `value` field (from [`streams-demo-producer`](../pyproject.toml))
- Uppercase `value` and write JSON back to `streams-output`
- Non-JSON payloads, missing `value`, or parse failures → `processed:` + `UCASE` of the full string (same as `StreamsPipelineApp.processJsonValue`)
- `SET 'processing.guarantee' = 'exactly_once'` for transactional consume–process–produce (ksqlDB EOS; analogous to Streams `exactly_once_v2`)

| Piece | Role |
|--------|------|
| [`sql/01_input_stream.sql`](sql/01_input_stream.sql) | `streams_input` on topic `streams-input` (`VALUE_FORMAT='KAFKA'`, raw `msg` VARCHAR) |
| [`sql/02_output_pipeline.sql`](sql/02_output_pipeline.sql) | CSAS `streams_output` → topic `streams-output` (persistent query) |
| [`scripts/deploy.sh`](scripts/deploy.sh) | Apply SQL via `ksql` CLI |
| [`scripts/terminate.sh`](scripts/terminate.sh) | Stop the CSAS query (edit query id if needed) |

Offset handoff after stopping ksqlDB (continue in Flink) is the same idea as [`../streams-handoff/`](../streams-handoff/README.md): read committed offsets for the ksqlDB consumer group on `streams-input`, then start Flink with `specific-offsets`.

## Prerequisites

- Confluent Cloud environment with a **Kafka** cluster and a **ksqlDB** cluster attached to it
- Topics `streams-input` and `streams-output` (create in Console or CLI; partition count should match your demo — often 6 on Cloud)
- **ksqlDB CLI** (`ksql` on `PATH`) — from [Confluent CLI](https://docs.confluent.io/confluent-cli/current/install.html) or Confluent Platform
- API key for the ksqlDB cluster (`KSQLDB_API_KEY` / `KSQLDB_API_SECRET`) and the cluster **HTTPS endpoint**

## Confluent Cloud setup

1. **Login and select environment / Kafka cluster** (same as main [README](../README.md)):

   ```bash
   confluent login
   confluent environment use "$CC_ENV_ID"
   confluent kafka cluster use lkc-...
   confluent kafka topic create streams-input
   confluent kafka topic create streams-output
   ```

2. **Create or use a ksqlDB cluster** linked to that Kafka cluster ([Console](https://docs.confluent.io/cloud/current/ksqldb/overview.html) or CLI):

   ```bash
   confluent ksql cluster list
   confluent ksql cluster describe <lksqlc-id>
   ```

   Note the **HTTP endpoint** (e.g. `https://pksqlc-xxxx.region.aws.confluent.cloud:443`).

3. **Create a ksqlDB API key** for the application:

   ```bash
   confluent api-key create --resource <lksqlc-id>
   ```

4. **Grant ACLs** for the ksqlDB service account on `streams-input` (read), `streams-output` (write), and consumer groups — see [ksqlDB Cloud config](https://docs.confluent.io/cloud/current/cp-component/ksql-cloud-config.html). The Console “ksqlDB cluster” wizard often sets this up; for CLI-only, allow `READ` on `streams-input`, `WRITE`/`CREATE` on `streams-output`, and `READ` on the `__consumer_offsets` / transactional internal topics as required by your org policy.

5. **Export variables** (add to `.env` if you like; not read automatically by the shell scripts):

   ```bash
   export KSQLDB_ENDPOINT='https://pksqlc-xxxx.region.aws.confluent.cloud:443'
   export KSQLDB_API_KEY='...'
   export KSQLDB_API_SECRET='...'
   ```

## Deploy the pipeline

From the repo root `kafka-topic-consumer-offsets/`:

```bash
chmod +x ksqldb/scripts/*.sh
./ksqldb/scripts/deploy.sh
```

Or run statements manually in the ksqlDB CLI:

```bash
ksql -u "$KSQLDB_API_KEY" -p "$KSQLDB_API_SECRET" "$KSQLDB_ENDPOINT"
```

```sql
RUN SCRIPT '/absolute/path/to/ksqldb/sql/00_session.sql';
RUN SCRIPT '/absolute/path/to/ksqldb/sql/01_input_stream.sql';
RUN SCRIPT '/absolute/path/to/ksqldb/sql/02_output_pipeline.sql';
```

Verify:

```sql
SHOW STREAMS;
SHOW QUERIES;
DESCRIBE streams_output EXTENDED;
```

## Demo (same data as kstream)

1. **Produce** JSON keyed by `device-1` … `device-5`:

   ```bash
   source .env   # KAFKA_BOOTSTRAP_SERVERS, KAFKA_API_KEY, KAFKA_API_SECRET
   uv run streams-demo-producer
   ```

2. **Consume output** (Python demo consumer or Console):

   ```bash
   uv run demo-kafka-consumer --topic streams-output --max-messages 10
   ```

   Expect JSON like `{"device_id":"device-5","value":"HELLO_5"}` (field order may differ from the Java serializer).

3. **Inspect ksqlDB consumer offsets** on the input topic (after stopping the query for handoff tests):

   ```bash
   uv run topic-consumer-offsets --topic streams-input --show-all-groups
   ```

   Find the consumer group for the CSAS query (`SHOW QUERIES` → `Query ID`, or `DESCRIBE <query id> EXTENDED` in ksqlDB). It is **not** `kstream-eos-demo`; ksqlDB uses names such as `_confluent-ksql-<cluster-id>query_CSAS_STREAMS_OUTPUT_0`.

## Stop the persistent query

```bash
./ksqldb/scripts/terminate.sh
```

If `TERMINATE` fails, run `SHOW QUERIES;` in ksqlDB and terminate the query id that backs `streams_output`.

To redeploy from scratch:

```sql
TERMINATE <query_id>;
DROP STREAM IF EXISTS streams_output DELETE TOPIC;  -- omit DELETE TOPIC to keep Kafka topic data
DROP STREAM IF EXISTS streams_input;
```

Then run `deploy.sh` again.

## Local Docker (optional)

ksqlDB on Confluent Cloud is the primary target. For a local ksqlDB + Kafka stack you would run ksqlDB Server against [`../docker-compose.yaml`](../docker-compose.yaml) and point `KSQLDB_ENDPOINT` at `http://localhost:8088` (no SASL). The SQL files are the same; use PLAINTEXT Kafka and create topics on the local broker. This repo does not ship a ksqlDB Server container — use Confluent Cloud or extend compose yourself.

## Parity with Kafka Streams

| Behavior | `kstream/` (Java) | `ksqldb/` |
|----------|-------------------|-----------|
| Input / output topics | `streams-input` / `streams-output` | Same |
| JSON `value` uppercase | Jackson `ObjectNode.put("value", upper)` | `UCASE(EXTRACTJSONFIELD(...))` + `AS_JSON(STRUCT(...))` |
| Fallback | `processed:` + `toUpperCase` on full string | Same `CASE` branches |
| Null value | `"[null]"` | `'[null]'` |
| Processing guarantee | `exactly_once_v2` | `processing.guarantee=exactly_once` |
| Application id / group | `kstream-eos-demo` | ksqlDB-generated CSAS consumer group |

## Note on transactions

As in the kstream README, **transactions** here means **ksqlDB / Kafka EOS** for the persistent query, not hand-written `beginTransaction()` in application code.
