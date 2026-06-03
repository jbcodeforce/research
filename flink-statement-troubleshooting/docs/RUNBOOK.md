# Runbook — Confluent Cloud Flink triage

Log results in [`notes.md`](../notes.md). See [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Step 1 — Verify tooling (no cluster)

```bash
cd flink-statement-troubleshooting
uv sync --extra dev
./assets/scripts/step1_verify.sh
```

---

## Step 2 — Confluent Cloud for Flink

```bash
cp .env.example .env   # CC + Flink + Kafka keys
confluent login
confluent kafka topic create perf-input
confluent kafka topic create perf-output
./assets/scripts/step2_deploy_cc.sh

uv run flink-triage run \
  --statement perf-dml-passthrough \
  --pool "$FLINK_COMPUTE_POOL_ID" \
  --output examples/live_report.md
```

Optional: failed-statement path with `assets/cc-flink/04_dml_broken.sql`.

---

## Scriptable tools

```bash
uv run flink-triage status -s perf-dml-passthrough --format json
uv run flink-triage metrics -s perf-dml-passthrough -p "$FLINK_COMPUTE_POOL_ID" --format json
uv run flink-triage run -s perf-dml-passthrough -p "$FLINK_COMPUTE_POOL_ID" --use-agno
```

Confluent MCP: `detect-flink-statement-issues`, `get-flink-statement-profile`.
