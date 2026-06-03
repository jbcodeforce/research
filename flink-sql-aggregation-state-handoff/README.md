# Flink SQL aggregation state handoff

Research study on Confluent Cloud: stop a global keyed Flink SQL aggregation, externalize state to an upsert sink topic, and deploy a new statement that bootstraps from that sink while continuing the source from stop offsets — avoiding full source replay from earliest.

## Research question

Can processing continue without reprocessing all source history from earliest offset?

Answer: Yes, for global keyed `SUM`/`COUNT` when v1 writes upsert state keyed by the group key, and v2 merges snapshot totals with incremental source events read via `specific-offsets` from `status.latest_offsets` at v1 stop. See [docs/PATTERNS.md](docs/PATTERNS.md).

On Confluent Cloud, end users cannot access savepoints (they are internal to Confluent for platform version migration). When you must deploy a new statement — different SQL or sink — sink-topic bootstrap is the practical user-controlled handoff. Stop/resume on the same statement can pause processing without changing the query, but it does not help statement replacement. Carry-over offsets and materialized-table evolution also do not preserve aggregation state across replacement.

## Scope

- Platform: Confluent Cloud Flink 2.2+
- Aggregation: global keyed `SUM(amount)` per `device_id`
- Topics: `device-events` → `agg-state-v1` → (handoff) → `agg-state-v2`

Out of scope: windowed aggregates, AVG/MIN/MAX merge, local OSS Flink.

## Architecture

```
v1:  device_events ──► GROUP BY device_id ──► agg_sink_v1 (upsert)
                              │
                         stop v1 statement
                              │
                    status.latest_offsets
                              │
v2:  agg_snapshot (sink replay) ──┐
     device_events (specific-offsets) ──► merge ──► agg_sink_v2
```

## Quickstart

```bash
cd flink-sql-aggregation-state-handoff
cp .env.example .env   # fill CC + Kafka credentials
uv sync --extra dev
uv run pytest tests/

./assets/cc-flink/deploy.sh v1
uv run state-handoff-produce --count 100 --keys 5
./assets/cc-flink/deploy.sh stop-v1
export SPECIFIC_OFFSETS="$(./assets/cc-flink/deploy.sh offsets)"
./assets/cc-flink/deploy.sh v2
uv run state-handoff-produce --count 50 --keys 5 --start-seq 100
```

Full runbook: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

## Utilities

| CLI | Purpose |
|-----|---------|
| `state-handoff-produce` | Emit keyed JSON events to `device-events` |
| `state-handoff-capture-offsets` | Format CC `latest_offsets` → `specific-offsets` hint |
| `state-handoff-validate` | Compare expected vs actual per-key totals |

## SQL assets

| File | Role |
|------|------|
| [01_ddl_source.sql](assets/cc-flink/01_ddl_source.sql) | Append source `device_events` |
| [02_ddl_sink_v1.sql](assets/cc-flink/02_ddl_sink_v1.sql) | Upsert sink v1 |
| [03_dml_v1_aggregate.sql](assets/cc-flink/03_dml_v1_aggregate.sql) | v1 aggregation |
| [04_ddl_snapshot.sql](assets/cc-flink/04_ddl_snapshot.sql) | Bootstrap from sink v1 topic |
| [05_ddl_sink_v2.sql](assets/cc-flink/05_ddl_sink_v2.sql) | Upsert sink v2 |
| [06_dml_v2_handoff.sql](assets/cc-flink/06_dml_v2_handoff.sql) | PRIMARY: FULL OUTER JOIN merge |
| [06b_dml_v2_handoff_fallback.sql](assets/cc-flink/06b_dml_v2_handoff_fallback.sql) | UNION ALL + SUM fallback |

## Findings

1. CC end users have no savepoint API; savepoints are Confluent-internal for version migration — not a user handoff tool.
2. CC carry-over offsets explicitly excludes aggregates; offset copy alone is insufficient for stateful handoff.
3. Upsert sink with PK = group key materializes recoverable per-key totals on a compacted topic — the user-controlled state export.
4. v2 merge adds `snapshot.total + incremental.delta` so keys with no post-stop events retain v1 totals (FULL OUTER JOIN).
5. Source `specific-offsets` avoids re-reading pre-stop events; cost shifts to replaying the smaller sink topic.
6. Cross-statement handoff is at-least-once; stop/resume on the same statement preserves opaque platform state but cannot change SQL or sink.

## Related work in this repo

- [kafka-topic-consumer-offsets/streams-handoff](../kafka-topic-consumer-offsets/streams-handoff/README.md) — stateless offset handoff
- [flink-statement-troubleshooting](../flink-statement-troubleshooting/README.md) — CC Flink deploy patterns

## Specification

See [SPEC.md](SPEC.md) for acceptance criteria and [notes.md](notes.md) for experiment log.
