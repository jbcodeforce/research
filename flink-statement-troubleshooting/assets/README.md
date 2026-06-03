# Perf-testing assets — Confluent Cloud Flink

SQL from [flink-studies perf-testing](https://github.com/jbcodeforce/flink-studies/tree/master/e2e-demos/perf-testing/flink-jobs/flink-sql), adapted for Confluent Cloud Kafka (SASL_SSL).

## Steps

| Step | Environment | Script |
|------|-------------|--------|
| 1 | Local CI (no Flink) | `scripts/step1_verify.sh` |
| 2 | Confluent Cloud Flink | `scripts/step2_deploy_cc.sh` |

See [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).

## Topics (CC Kafka)

- Input: `perf-input`
- Output: `perf-output`

## Statements

| File | Statement name | Purpose |
|------|----------------|---------|
| `cc-flink/01_ddl_perf_source.sql` | `perf-ddl-source` | Kafka source |
| `cc-flink/02_ddl_perf_sink.sql` | `perf-ddl-sink` | Kafka sink |
| `cc-flink/03_dml_passthrough.sql` | `perf-dml-passthrough` | Healthy streaming job |
| `cc-flink/04_dml_broken.sql` | `perf-dml-broken` | FAILED triage demo |

## Producer (optional)

Run flink-studies DataGenerator against your **Confluent Cloud** bootstrap to populate metrics. Not a local Flink deployment.

## Triage

```bash
uv run flink-triage run -s perf-dml-passthrough -p $FLINK_COMPUTE_POOL_ID
```
