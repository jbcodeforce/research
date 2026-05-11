# Research: Flink benchmark methodology and execution plan

## Intent

This research defines and executes a repeatable Apache Flink benchmark focused on:

- throughput ceilings,
- latency behavior under checkpointing,
- scaling efficiency across parallelism levels,
- state backend trade-offs for keyed workloads.

The benchmark is Python-first (`uv` + Python orchestration), with optional Java baselines only when existing open-source tools provide useful reference points.

## Scope

In scope:

- Workload definitions `W1`, `W2`, `W3` from `SPEC.md`.
- Smoke and research benchmark profiles.
- Repeatable run procedure and result artifacts.
- Practical interpretation guidance for findings.

Out of scope:

- Cross-engine comparisons.
- Production capacity commitments for all environments.

## Inputs and constraints

- Specification source: `SPEC.md`.
- Notes and decisions log: `notes.md`.
- Python-first tooling requirement from repository guidance.
- Java is allowed only as a secondary baseline using existing OSS benchmarks.

## Workloads

### W1: Stateless micro pipeline
- `datagen -> map/filter -> blackhole`
- Purpose: operator compute ceiling with minimal external bottlenecks.

### W2: Kafka ingest transform
- `kafka source -> parse/map -> blackhole`
- Purpose: realistic ingest and backpressure behavior.

### W3: Stateful keyed windows
- `datagen|kafka -> keyBy -> window/stateful aggregate -> blackhole`
- Purpose: state backend and skew sensitivity under checkpointing.

## Benchmark profiles

### Smoke profile
Use for fast validation and harness sanity checks.

- `parallelism`: `2, 4`
- `source_rate_rps`: `10k, 50k`
- `checkpoint_interval_ms`: `0, 60000`
- `state_backend`: `hashmap`
- `run_repetitions`: `2`

### Research profile
Use for full data collection and conclusions.

- `parallelism`: `2, 4, 8, 16`
- `source_rate_rps`: `10k, 50k, 100k, 200k`
- `checkpoint_interval_ms`: `0, 60000, 300000`
- `checkpoint_unaligned`: `false, true` when checkpointing is enabled
- `state_backend`: `hashmap, rocksdb` (`W3` mandatory for both)
- `key_cardinality`: `1k, 100k, 1M` (`W3`)
- `key_skew_mode`: `uniform, hotspot` (`W3`)
- `run_repetitions`: `3` minimum

## Prerequisites

- Docker + Docker Compose (for local reproducible cluster setup).
- Flink runtime in Docker or local cluster.
- Python 3.11+.
- `uv` package manager.
- Optional:
  - Kafka cluster (local or cloud) for `W2`.
  - Prometheus/Grafana for metrics visualization.
  - Java + Maven only for optional external benchmark baseline.

## Standard run variables

Each run must set and record:

- `workload_id` (`W1|W2|W3`)
- `profile_id` (`smoke|research`)
- `parallelism`
- `taskmanager_slots`
- `source_rate_rps`
- `payload_bytes`
- `key_cardinality`
- `key_skew_mode`
- `checkpoint_interval_ms`
- `checkpoint_unaligned`
- `state_backend`
- `run_warmup_sec`
- `run_measurement_sec`
- `run_repetitions`

## Execution runbook

### 1) Environment setup

```bash
cd /Users/jerome/Documents/Code/research/flink-benchmark
uv sync
```

If using local infrastructure, start dependencies (Kafka/Flink/Prometheus) according to your chosen compose or deployment files.

### 2) Smoke pass

Run at least one full smoke sweep before the research profile:

```bash
uv run python -m benchmark_harness.run --profile smoke --workloads W1,W2,W3
```

Expected outcome:

- all required metrics are produced,
- no missing artifact fields,
- throughput variance is acceptable for repeated runs.

### 3) Full research pass

```bash
uv run python -m benchmark_harness.run --profile research --workloads W1,W2,W3
```

### 4) Summarize and compare

```bash
uv run python -m benchmark_harness.report --input results --output results/summary.md
```

The reporting step should generate profile-level comparisons for:

- scaling efficiency by workload,
- checkpoint latency/throughput deltas,
- `hashmap` vs `rocksdb` for `W3`.

## Output structure

Use the following artifact format:

- `results/<run_id>.json`
- `results/<run_id>.md`
- `results/summary.md`

Each `<run_id>.json` should include:

- metadata:
  - `run_id`
  - `timestamp_utc`
  - `flink_version`
  - `workload_id`
  - `profile_id`
- configuration:
  - `variables` object with all run variables
- measurements:
  - `metrics` object for throughput/latency/checkpoint/resource/backpressure
- derived:
  - `throughput_stability_cv`
  - `scale_efficiency`
  - `checkpoint_latency_penalty`
- traceability:
  - `notes_ref` pointer into `notes.md`

## Result interpretation guide

When reading results:

1. Verify reproducibility first (`throughput_stability_cv` and repeatability).
2. Compare W1 vs W2 to separate Flink compute capacity from broker/network limits.
3. For checkpoint experiments, prioritize p95/p99 changes over averages.
4. Use scaling efficiency to detect diminishing returns early.
5. For W3, evaluate backend trade-offs by cardinality and skew; a backend that is slower at low cardinality may become more stable at high cardinality.

## Limitations

- Local-machine benchmarks can be noisy.
- JIT and GC behavior can affect early windows.
- Kafka bottlenecks can hide operator capacity.
- Benchmark outputs are environment-specific and should not be generalized without replication.

## Next steps

- Implement the Python benchmark harness module and report generator.
- Add a default Docker profile for one-command local execution.
- Add optional Java OSS baseline runs for cross-checking selected scenarios.
- Promote stable findings into a compact benchmark cookbook in this repository.
