# Notes — multi-tenant Debezium span-out PTF

## 2026-05-26 — Project start

- Flow: fan-out (inverse of denormalizer), shared tables with `tenant_id`.
- PTF completion uses Debezium END `event_count` + `receivedEventCount` (same as reference PTF).
- Per-tenant physical sinks are SQL filters on unified fan-out stream.

## Implementation

- `TransactionSpanOutLogic` extracted for unit tests without Flink runtime.
- Mock producer keys messages by `transaction.id` for partition alignment with `PARTITION BY transaction_id`.

## Confluent Cloud

- Upload shaded JAR via `confluent flink artifact create`.
- Register with `CREATE FUNCTION ... USING JAR 'confluent-artifact://...'`.
- Confirm Flink 2.2+ compute pool (PTF requires ProcessTableFunction support).

## Verification (2026-05-26)

- `mvn -f ptf/pom.xml test package` — pass (4 JUnit tests).
- `uv run pytest` — pass (3 tests).
- `docker compose build` — image `mt-spanout-flink:latest` builds successfully.
- Local `docker compose up` may fail if host port 9092 is already in use; stop other Kafka stacks or change the broker port mapping.
