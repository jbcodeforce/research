# Flink SQL aggregation state handoff — specification

## Research question

Can you stop a stateful Flink SQL global keyed aggregation, preserve aggregate state via an upsert sink topic, and deploy a new statement that bootstraps from that sink and continues the source from stop offsets — without reprocessing the full source from earliest?

## Runtime scope

Confluent Cloud for Flink only. Flink 2.2+, Confluent Platform Kafka 8.2+ on CC.

## Confluent Cloud constraint (savepoints)

End users on Confluent Cloud do not have access to savepoints. Savepoints are used internally by Confluent during product version-to-version migration — not exposed as a user-operable API for statement replacement or DR. This study therefore focuses on sink-topic bootstrap as the practical end-user path when deploying a new statement.

## Topology

| Stage | Statement | Role |
|-------|-----------|------|
| v1 | `handoff-ddl-source`, `handoff-ddl-sink-v1`, `handoff-dml-v1` | `device_events` → global `SUM(amount)` → `agg_sink_v1` (upsert) |
| stop | REST `spec.stopped=true` | Capture `status.latest_offsets` |
| v2 | `handoff-ddl-snapshot`, `handoff-ddl-sink-v2`, `handoff-dml-v2` | Bootstrap from sink topic + incremental source → `agg_sink_v2` |

## Aggregation shape

Global keyed aggregate: `GROUP BY device_id` with `SUM(amount)` and `MAX(event_time)`.

Out of scope: windowed aggregates, AVG/MIN/MAX merge math.

## Acceptance criteria

1. **AC1 — v1 correctness:** `agg_sink_v1` per-key totals match offline expected sums after producing events.
2. **AC2 — handoff correctness:** After stop → v2 → more events, `agg_sink_v2` equals v1 totals plus new deltas per key.
3. **AC3 — no full replay:** v2 source uses `specific-offsets` from v1 stop metadata, not `earliest-offset` on the source topic.
4. **AC4 — documentation:** README answers the research question; `docs/PATTERNS.md` compares stop/resume (same statement only), sink bootstrap, and full replay — and documents that savepoints are not user-accessible on CC.
5. **AC5 — tests:** `uv run pytest tests/` passes for validator and offset formatting.

## Baselines (document only)

- Same-statement stop/resume (platform-managed internal state; not user-visible savepoints; SQL and sink unchanged).
- Full source replay (`earliest-offset` on source only).

## Non-goals

- Local OSS Flink cluster
- Exactly-once guarantees across two independent statements
- Windowed or non-SUM aggregation handoff
