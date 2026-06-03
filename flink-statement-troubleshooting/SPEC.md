# Flink statement triage — specification

## Intent

Diagnose Confluent Cloud Flink SQL statement issues using metrics, REST status, exceptions, and rule-based analysis.

## Runtime scope

Confluent Cloud for Flink only. No local Flink cluster, no Kubernetes Flink deployment in this project.

## Inputs (standalone)

| Field | Required | Default |
|-------|----------|---------|
| `statement_name` | yes | — |
| `compute_pool_id` | yes | `$FLINK_COMPUTE_POOL_ID` |
| `time_window` | no | 30 minutes |

## Workflow

1. Step 1 — verify `flink-triage` offline (`step1_verify.sh`)
2. Step 2 — deploy CC SQL + run live triage (`step2_deploy_cc.sh`)

## Acceptance criteria

1. `uv run pytest tests/` passes.
2. `./assets/scripts/step1_verify.sh` completes.
3. `step2_deploy_cc.sh` + live `flink-triage run` documented for Confluent Cloud.
4. [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) describes CC-only deployment.

## Out of scope

- shift_left_utils pipeline inventory
- Local OSS Flink
- Kubernetes Flink
