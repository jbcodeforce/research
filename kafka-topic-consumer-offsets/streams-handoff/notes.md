# Notes (streams-handoff)

## 2026-04-27

- Added `streams_demo_producer.py` + `uv run streams-demo-producer`: five keys `device-1`..`device-5`, JSON value `{"device_id","value"}` for Flink JSON DDL; Kafka key = `device_id` bytes.
- Kafka Streams still treats the value as one string, so it uppercases the **entire JSON text** on `streams-output` when KS runs—fine for a pipeline demo; Flink SQL parses JSON and uppercases only the `value` field in the handoff example.
- Flink 2.2 docs: `scan.startup.specific-offsets` as `partition:0,offset:N;...` (see `flink/continue_from_offsets.sql`).
- Offset source after stopping KS: consumer group `kstream-eos-demo` on topic `streams-input` (same group used by `KAFKA_STREAMS_APPLICATION_ID`).
