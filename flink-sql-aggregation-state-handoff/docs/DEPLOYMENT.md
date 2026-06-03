# Deployment guide — Confluent Cloud only

All SQL runs on Confluent Cloud for Flink (Flink 2.2+). No local Flink cluster.

## Prerequisites

- Confluent CLI logged in (`confluent login`)
- Flink compute pool on CC
- API keys: Flink (regional), Kafka cluster (SASL_SSL)
- `envsubst` (gettext), `uv`, `confluent` CLI

## Configure

```bash
cd flink-sql-aggregation-state-handoff
cp .env.example .env
# Fill CC_ORG_ID, CC_ENV_ID, FLINK_COMPUTE_POOL_ID, FLINK_API_KEY/SECRET,
# BOOTSTRAP_SERVERS, KAFKA_API_KEY/SECRET, CLOUD_REGION
uv sync --extra dev
```

## End-to-end handoff workflow

### 1. Deploy v1 (aggregation pipeline)

```bash
chmod +x assets/cc-flink/deploy.sh
./assets/cc-flink/deploy.sh v1
```

Statements created:

| Name | SQL file |
|------|----------|
| `handoff-ddl-source` | `01_ddl_source.sql` |
| `handoff-ddl-sink-v1` | `02_ddl_sink_v1.sql` |
| `handoff-dml-v1` | `03_dml_v1_aggregate.sql` |

Wait until `handoff-dml-v1` is RUNNING.

### 2. Produce phase-1 events

```bash
uv run state-handoff-produce --count 100 --keys 5
```

Verify in Flink SQL shell or Console:

```sql
SELECT * FROM agg_sink_v1;
```

Optionally export sink records to JSON for later validation.

### 3. Stop v1 and capture source offsets

```bash
./assets/cc-flink/deploy.sh stop-v1
```

Wait until statement phase is `STOPPED`. CC exposes `status.latest_offsets` for source tables. (Savepoints are not user-accessible on CC; they are internal to Confluent for platform version migration.)

Capture offsets as a Flink `specific-offsets` hint:

```bash
./assets/cc-flink/deploy.sh offsets
# or offline from saved API response:
uv run state-handoff-capture-offsets --json-file tests/fixtures/statement_latest_offsets.json
```

### 4. Deploy v2 (handoff pipeline)

```bash
export SPECIFIC_OFFSETS="$(./assets/cc-flink/deploy.sh offsets)"
./assets/cc-flink/deploy.sh v2
```

v2 reads:

- `agg_snapshot` from `agg-state-v1` topic (`earliest-offset`, upsert bootstrap)
- `device_events` from stop offsets only (`specific-offsets`)

Output goes to `agg-state-v2` topic.

### 5. Produce phase-2 events and validate

```bash
uv run state-handoff-produce --count 50 --keys 5 --start-seq 100
```

Validate totals (after consuming sink JSON from Kafka):

```bash
uv run state-handoff-validate \
  --baseline path/to/v1_sink.json \
  --incremental path/to/phase2_events.json \
  --actual path/to/v2_sink.json
```

### 6. Fallback SQL

If `06_dml_v2_handoff.sql` fails on CC (e.g. FULL OUTER JOIN rejected), deploy `06b_dml_v2_handoff_fallback.sql` instead by editing `deploy.sh` or submitting manually with the same `SPECIFIC_OFFSETS` substitution.

## Statement lifecycle commands

```bash
confluent flink statement list --environment "$CC_ENV_ID" --compute-pool "$FLINK_COMPUTE_POOL_ID"
confluent flink statement describe handoff-dml-v1 --environment "$CC_ENV_ID" --compute-pool "$FLINK_COMPUTE_POOL_ID"
confluent flink statement stop handoff-dml-v1 --environment "$CC_ENV_ID" --compute-pool "$FLINK_COMPUTE_POOL_ID"
```

## Stop/resume baseline (same statement only)

To pause and resume without changing SQL or sink (not a new-statement handoff):

1. Stop `handoff-dml-v1` (`deploy.sh stop-v1`)
2. Resume: `confluent flink statement resume handoff-dml-v1 ...`

The platform preserves opaque internal state; users cannot access savepoint paths or artifacts. This does not apply when deploying v2 as a replacement statement. See [docs/PATTERNS.md](PATTERNS.md).

## Checklist

Log in [notes.md](../notes.md):

- [ ] v1 deployed and RUNNING
- [ ] Phase-1 events produced, v1 totals verified
- [ ] v1 stopped, offsets captured
- [ ] v2 deployed with `SPECIFIC_OFFSETS`
- [ ] Phase-2 events produced, validation passed
