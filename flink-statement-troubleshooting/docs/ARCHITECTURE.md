# Architecture

## Scope

Confluent Cloud for Flink only. The CLI talks to CC Flink REST and the Metrics API. Step 1 uses fixtures; there is no local Flink runtime.

## Layers

1. **Core library** — `flink_rest`, `metrics_client`, `flink_queries`, `report`
2. **Tools** — `flink_stmt_triage.tools`
3. **Orchestration** — `triage_runner` or `agents/team` (Agno + LLM)
4. **CLI** — `flink-triage`

## Agno Team

| Agent | Tools | Role |
|-------|-------|------|
| StatementStatusAgent | status, exceptions, health | Phase and errors |
| MetricsAgent | statement metrics, pool CFU | Throughput and capacity |
| ProfilerAgent | issue detection, profile stub | Bottleneck hints |
| Lead (TeamMode.coordinate) | synthesizes | Final markdown report |

## Data flow

```
statement_name + compute_pool_id
    → CC Flink REST (phase, exceptions)
    → CC Metrics API (in/out/pending/state/CFU)
    → rule-based hypotheses + actions
    → TriageReport (markdown + JSON)
```

## Debug fixture

Perf-testing passthrough in [`assets/cc-flink/`](../assets/cc-flink/). Primary statement: `perf-dml-passthrough`.
