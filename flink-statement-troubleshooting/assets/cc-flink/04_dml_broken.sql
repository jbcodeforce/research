-- Intentional syntax error for FAILED triage demo (statement name: perf-dml-broken).

INSERT INTO perf_sink
SELECT id, event_time, value, payload INVALID_SYNTAX
FROM perf_source;
