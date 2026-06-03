# Working notes — Flink SQL aggregation state handoff

## 2026-06-03 — Project scaffold

- Created research folder per plan: CC Flink only, global keyed SUM aggregate.
- Primary v2 pattern: `FULL OUTER JOIN` between incremental source subquery (`specific-offsets`) and `agg_snapshot` upsert table (`earliest-offset` on sink topic).
- Fallback: `06b_dml_v2_handoff_fallback.sql` uses UNION ALL snapshot seed + new events, then SUM.

## 2026-06-03 — Local verification (no CC cluster)

- `uv run pytest tests/` — 16 tests passed (offsets, produce, validate, deploy assets).
- Offline handoff math validated via `merge_handoff_totals`: baseline v1 totals + phase-2 events = expected v2 totals.
- `capture_offsets` roundtrip tested against `tests/fixtures/statement_latest_offsets.json`.

## CC experiment checklist

Run manually when CC credentials are available (see `docs/DEPLOYMENT.md`):

- [ ] Create topics `device-events`, `agg-state-v1`, `agg-state-v2`
- [ ] Deploy v1 DDL + DML
- [ ] `uv run state-handoff-produce --count 100 --keys 5`
- [ ] Validate v1 via `SELECT * FROM agg_sink_v1` or Kafka consume
- [ ] Stop `handoff-dml-v1`, capture offsets with `./assets/cc-flink/deploy.sh offsets`
- [ ] Deploy v2 with `SPECIFIC_OFFSETS` env var
- [ ] Produce 50 more events with `--start-seq 100`
- [ ] Run `state-handoff-validate` against consumed sink JSON

## 2026-06-03 — CC savepoint clarification

- End users on Confluent Cloud have no access to savepoints.
- Savepoints are Confluent-internal, used for product version-to-version migration.
- User-operable handoff for new statement deployment = sink-topic bootstrap (Pattern B) + `status.latest_offsets`.
- Stop/resume on same statement is pause-only; does not help SQL/sink replacement.

## Findings (research conclusion)

### Can we avoid reprocessing source from earliest?

Yes, with Pattern B (sink-topic bootstrap):

1. v1 writes per-key totals to upsert sink (`agg-state-v1`).
2. On stop, CC exposes `status.latest_offsets` for `device_events`.
3. v2 reads sink from earliest (compact topic, one row per key after replay) and source from `specific-offsets`.
4. Merge SQL produces correct totals without scanning pre-stop source events.

### When not to use Pattern B

- Same SQL and sink, pause only: stop/resume same statement (no savepoint API for users).
- No upsert sink in v1: add one first, or accept full source replay.
- Windowed aggregates: state shape differs; deferred.

### CC SQL risks to validate live

- FULL OUTER JOIN between incremental grouped subquery and upsert snapshot may need fallback 06b.
- Bootstrap replay of upsert topic still incurs ChangelogNormalize cost during v2 startup.
- Offset boundary must match v1 stop exactly to avoid double-count or gaps.

## References

- CC carry-over offsets: excludes aggregates
- CC schema-statement-evolution: `latest_offsets` on stop
- CC materialized table ALTER: discards stateful state, reprocesses source
