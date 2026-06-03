---
name: flink-statement-triage
description: >-
  Troubleshoot Confluent Cloud Flink SQL statements using flink-triage CLI,
  metrics, and exceptions. Use when a statement is FAILED, PENDING, has
  backpressure, zero output, or high state size.
---

# Flink statement triage

## Scope

Confluent Cloud for Flink only. No local or K8s Flink runtime.

## When to use

User reports CC Flink statement failure, stuck deployment, lag, or asks to analyze a named statement.

## Required inputs

- `statement_name` (e.g. `perf-dml-passthrough`)
- `compute_pool_id` (e.g. `lfcp-xxxxx`)

## Workflow

1. **Step 1** — `./assets/scripts/step1_verify.sh` (offline, no cluster)
2. **Step 2** — `./assets/scripts/step2_deploy_cc.sh` then live triage

See [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md).

## Triage commands

```bash
uv run flink-triage run --statement NAME --pool POOL
uv run flink-triage run -s perf-dml-passthrough -p lfcp-example --dry-run  # Step 1 only
```

Confluent MCP: `detect-flink-statement-issues`, `get-flink-statement-profile`.

## References

- [`docs/DEPLOYMENT.md`](../docs/DEPLOYMENT.md)
- [`docs/RUNBOOK.md`](../docs/RUNBOOK.md)
