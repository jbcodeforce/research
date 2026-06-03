-- Healthy passthrough DML — primary UAT target (statement name: perf-dml-passthrough).
-- Run after 01_ddl_perf_source.sql and 02_ddl_perf_sink.sql.

INSERT INTO perf_sink
SELECT id, event_time, value, payload
FROM perf_source;
