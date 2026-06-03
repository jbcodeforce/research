# Flink statement troubleshooting agent

Agno Team CLI and reusable tools for diagnosing **Confluent Cloud for Flink** SQL statement issues.

## Scope

Confluent Cloud only. Step 1 verifies the CLI offline (no Flink cluster); Step 2 deploys to and triages against Confluent Cloud.

## Two-step workflow

| Step | What | Command |
|------|------|---------|
| 1 | Verify tooling (dry-run, no cluster) | `./assets/scripts/step1_verify.sh` |
| 2 | Deploy + live triage on CC Flink | `./assets/scripts/step2_deploy_cc.sh` then `flink-triage run` |

Details: [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

## Quickstart

```bash
cd flink-statement-troubleshooting
uv sync --extra dev
./assets/scripts/step1_verify.sh
```

## Confluent Cloud (Step 2)

```bash
cp .env.example .env
./assets/scripts/step2_deploy_cc.sh
uv run flink-triage run -s perf-dml-passthrough -p "$FLINK_COMPUTE_POOL_ID"
```

## Debug fixture

Perf-testing passthrough SQL in [`assets/cc-flink/`](assets/cc-flink/), adapted from [flink-studies perf-testing](https://github.com/jbcodeforce/flink-studies/tree/master/e2e-demos/perf-testing). Topics: `perf-input` / `perf-output` on your CC Kafka cluster.

## CLI

| Command | Purpose |
|---------|---------|
| `flink-triage run` | Full triage (`--dry-run`, `--use-agno`) |
| `flink-triage status` | Statement phase |
| `flink-triage metrics` | Metrics snapshot |
| `flink-triage exceptions` | Recent exceptions |
| `flink-triage tools list` | Tool schemas |

## Documentation

- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — Confluent Cloud deployment
- [`SPEC.md`](SPEC.md) — scenarios and acceptance criteria
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — layers and Agno team
- [`docs/TOOLS.md`](docs/TOOLS.md) — Hermes / Claude Code / MCP
- [`skill/SKILL.md`](skill/SKILL.md) — Cursor playbook

## Findings

- Tooling can be verified offline; live triage requires Confluent Cloud credentials.
- Metrics API and Flink REST target CC endpoints only.
- Full Query Profiler task graphs require Confluent MCP or Console.
