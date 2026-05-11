# Flink benchmark specification

## Purpose

Define a repeatable benchmark methodology to measure Flink throughput, latency, scaling behavior, and checkpoint/state overhead under controlled conditions.

This specification is implementation-ready and designed for local or containerized execution with Python-first tooling.

## Research questions and hypotheses

### RQ1: Throughput ceiling
How much sustained throughput can each workload profile process before persistent backpressure appears?

Hypothesis H1:
Datagen + blackhole workloads will sustain materially higher throughput than Kafka-based workloads because broker/network I/O is removed from the critical path.

### RQ2: Latency under fault-tolerance settings
What is the p95/p99 end-to-end latency impact of checkpoint configuration choices?

Hypothesis H2:
Short checkpoint intervals reduce recovery point objective but increase p99 latency and checkpoint alignment overhead.

### RQ3: Scaling linearity
How close to linear speedup does each workload achieve when increasing parallelism and TaskManagers?

Hypothesis H3:
Simple stateless workloads scale near-linearly; keyed/stateful workloads show diminishing returns due to shuffle, state access, and skew.

### RQ4: State backend trade-offs
How do `HashMapStateBackend` and RocksDB differ for latency and throughput as keyed state grows?

Hypothesis H4:
`HashMapStateBackend` wins for low/medium state, while RocksDB is more stable when state size or cardinality grows beyond memory-friendly bounds.

## Non-goals

- This research does not claim production capacity numbers for all environments.
- This research does not optimize every operator implementation detail.
- This research does not compare Flink against other streaming engines.

## Benchmark architecture

Each run must include:

1. Source:
   - synthetic data (`datagen`) for compute/state isolation,
   - Kafka source for realistic I/O scenarios.
2. System under test:
   - Flink job with workload-specific transformations, optional windows/state.
3. Sink:
   - `blackhole` for capacity tests,
   - optional Kafka sink for I/O round-trip scenarios.
4. Metrics collection:
   - Flink metrics endpoint + Prometheus scraping.
5. Result materialization:
   - structured run artifact (`results/<run_id>.json`) and markdown summary.

## Workload catalog

Use stable workload IDs in all docs, scripts, and result files.

### W1: Stateless micro pipeline
- Topology: `datagen -> map/filter -> blackhole`
- Goal: measure operator compute ceiling with minimal external bottlenecks.

### W2: Kafka ingest transform
- Topology: `kafka source -> parse/map -> blackhole`
- Goal: capture realistic source overhead and backpressure behavior.

### W3: Stateful keyed windows
- Topology: `datagen|kafka -> keyBy -> windowed aggregate/state access -> blackhole`
- Goal: measure state access and checkpoint interactions under variable cardinality.

## Controlled variables

For each run, record exact values for:

- `parallelism`
- `taskmanager_slots`
- `source_rate_rps`
- `payload_bytes`
- `key_cardinality`
- `key_skew_mode` (`uniform`, `hotspot`)
- `checkpoint_interval_ms` (`0` means disabled)
- `checkpoint_unaligned` (`true|false`)
- `state_backend` (`hashmap`, `rocksdb`)
- `run_warmup_sec`
- `run_measurement_sec`
- `run_repetitions`

## Baseline matrix

Use two profiles to control effort.

### Smoke profile (fast validation)
- `parallelism`: 2, 4
- `source_rate_rps`: 10k, 50k
- `checkpoint_interval_ms`: 0, 60000
- `state_backend`: `hashmap`
- repetitions: 2

### Research profile (full study)
- `parallelism`: 2, 4, 8, 16
- `source_rate_rps`: 10k, 50k, 100k, 200k
- `checkpoint_interval_ms`: 0, 60000, 300000
- `checkpoint_unaligned`: false, true (when checkpointing enabled)
- `state_backend`: `hashmap`, `rocksdb` (for W3 mandatory)
- `key_cardinality`: 1k, 100k, 1M (W3)
- `key_skew_mode`: uniform, hotspot (W3)
- repetitions: 3 (minimum)

## Metrics and derived indicators

Minimum captured metrics per run:

- throughput:
  - `numRecordsInPerSecond`
  - `numRecordsOutPerSecond`
- latency:
  - end-to-end p50/p95/p99 (workload-specific implementation)
- checkpoint:
  - checkpoint duration
  - alignment time
  - failed checkpoints
- pressure and utilization:
  - backpressured time ratio
  - busy/idle time ratio
  - CPU, heap, managed/off-heap memory

Derived indicators:

- `throughput_stability_cv` (coefficient of variation over measurement windows)
- `scale_efficiency = throughput_n / (throughput_1 * n)`
- `checkpoint_latency_penalty = p99_with_ckpt / p99_without_ckpt`

## Run procedure

1. Validate environment and versions.
2. Deploy selected profile and workload.
3. Warmup phase (ignore metrics in analysis).
4. Measurement phase (collect and persist metrics).
5. Repeat run `N` times with the same parameters.
6. Compute median + spread across repetitions.
7. Save artifacts and summary.

## Acceptance criteria

### AC1: Reproducibility
- Every result row can be tied to exact workload ID and variable set.
- Same run parameters produce comparable numbers across repetitions (throughput CV <= 15% in smoke runs unless justified in notes).

### AC2: Observability completeness
- Required throughput, latency, checkpoint, and pressure metrics are present for each run.

### AC3: Scaling evidence
- For each workload in research profile, include at least one scale-efficiency chart/table over parallelism.

### AC4: Checkpoint trade-off evidence
- At least one workload includes comparison with checkpoint disabled vs enabled settings, with explicit p99 and throughput deltas.

### AC5: State backend evidence
- W3 includes both `hashmap` and `rocksdb` runs with same cardinality/skew settings and an explicit comparison summary.

## Tooling strategy

Primary implementation path:

- Python orchestration and analysis scripts.
- PyFlink/Table API job definitions when practical.
- `uv` for Python environment and commands.

Optional Java path:

- Use existing open-source benchmark tools (for example Nexmark/Flink-runner-based baselines) when they reduce implementation effort or provide trusted reference comparisons.
- Avoid custom Java benchmark code unless Python path cannot cover a required scenario.

## Threats to validity and mitigations

- Local machine noise:
  - Mitigate by dedicated host profile, repeated runs, and recording host load.
- JIT/GC warmup effects:
  - Use explicit warmup period and exclude warmup metrics.
- Kafka broker bottlenecks hiding Flink limits:
  - Include datagen baseline and compare against Kafka workload.
- Data skew artifacts:
  - Test both uniform and hotspot key distributions.

## Artifact schema

Each run produces:

- `results/<run_id>.json` with:
  - `run_id`
  - `timestamp_utc`
  - `flink_version`
  - `workload_id`
  - `profile_id` (`smoke` or `research`)
  - `variables` (all controlled variables)
  - `metrics` (raw and aggregated)
  - `derived` (derived indicators)
  - `notes_ref` (pointer to `notes.md` entry)
- `results/<run_id>.md` human summary for quick review.

## Exit criteria for this research phase

Research phase is complete when:

- smoke profile runs are stable and reproducible,
- research profile has at least one complete pass for W1/W2/W3,
- README report contains method, key findings, caveats, and recommended next experiments.