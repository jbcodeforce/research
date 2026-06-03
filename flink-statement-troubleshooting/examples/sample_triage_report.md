# Flink statement triage: perf-dml-passthrough

## Summary
- Phase: RUNNING
- Severity: info
- Compute pool: lfcp-example

Statement `perf-dml-passthrough` is in phase **RUNNING** with severity **info**. Collected 6 metric series and 0 exception record(s).

## Evidence

| Source | Finding |
|--------|---------|
| flink_rest | phase=RUNNING; detail=Statement is running. |
| metrics | num_records_in=400.0 (rising) |
| metrics | num_records_out=390.0 (rising) |
| metrics | pending_records=0.0 (flat) |
| metrics | statement_status=1.0 (flat) |
| metrics | state_size_bytes=1024.0 (flat) |
| metrics | pool_current_cfus=2.0 (flat) |

## Metrics

| Metric | Latest | Trend |
|--------|--------|-------|
| num_records_in | 400.0 | rising |
| num_records_out | 390.0 | rising |
| pending_records | 0.0 | flat |
| statement_status | 1.0 | flat |
| state_size_bytes | 1024.0 | flat |
| pool_current_cfus | 2.0 | flat |

## Hypotheses

1. No obvious issue from available signals; statement appears healthy.
   - If true: Continued monitoring of metrics will detect regressions.

## Recommended actions

1. Continue monitoring metrics; re-run triage if phase or lag changes.
