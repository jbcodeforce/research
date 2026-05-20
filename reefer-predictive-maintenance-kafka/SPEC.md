# Reefer predictive maintenance — Kafka streams ML (research SPEC)

This document specifies a research proof of concept under `research/reefer-predictive-maintenance-kafka/`. It demonstrates how to develop a **predictive maintenance** machine learning workflow for refrigerated transport units (reefers) using an **event-streaming** architecture where **training and test telemetry share one Kafka topic** and are separated only by record metadata and stream processing logic.

For research folder conventions (Python, `uv`, TDD, `notes.md`, `README.md`), see [AGENTS.md](../AGENTS.md).

Related prior art in this workspace:

- [flink-studies/code/flink-sql/12-ai-agents/](https://github.com/jbcodeforce/flink-studies/tree/master/code/flink-sql/12-ai-agents/) — reefer temperature **anomaly detection** (ARMA in Flink SQL; Faker source).
- [kafka-topic-consumer-offsets/](../kafka-topic-consumer-offsets/) — Kafka ops and stream handoff patterns.

This project differs by focusing on **supervised failure prediction** (degraded / failure-imminent labels), a **single telemetry topic** for train and test, and an explicit **stream-native ML lifecycle** (feature windows, train trigger, evaluate, score).

---

## Problem statement

Cold-chain operators need to act on reefer health **before** a hard failure (compressor trip, refrigerant loss, sustained out-of-range temperature). Batch retraining on nightly extracts is common but lags the stream. This research asks:

> How do you train and evaluate a predictive maintenance model when **all** telemetry (train, test, and live scoring) flows through **one** Kafka topic, and stream processors route records by role without copying data to separate train/test topics?

The answer is a **unified event contract** plus **stream-side filtering and windowed feature extraction**, not topic proliferation.

---

## Goals

1. **Single topic contract** — Producers emit labeled training rows, labeled test rows, and unlabeled inference rows on `reefer.telemetry.v1` (name configurable), distinguished by `meta.split` and related fields.
2. **Stream feature pipeline** — Per-`device_id` tumbling (or hopping) windows compute maintenance-oriented features (temperature deltas, rate of change, door events, power drift).
3. **Train from the stream** — A training consumer (or stream task) reads only `meta.split = 'train'`, fits a baseline classifier, persists model artifact version `vNNN`.
4. **Test from the same topic** — An evaluation path reads only `meta.split = 'test'`, scores with the persisted model, emits metrics (precision/recall/F1, confusion matrix) to `reefer.ml.metrics.v1`.
5. **Score live telemetry** — Inference records (`meta.split = 'inference'`, `meta.is_labeled = false`) are scored in near real time; predictions go to `reefer.ml.predictions.v1`.
6. **Reproducible local stack** — Docker Compose Kafka (KRaft, CP 8.2.0+), synthetic reefer generator, `uv`-managed Python; optional Java Kafka Streams module documented but not required for baseline acceptance.
7. **Document the pattern** — `README.md` explains why one topic is enough, how leakage is avoided, and how this maps to “training stream + test stream + inference stream” patterns described in streaming ML literature.

---

## Non-goals

| Topic | Rationale |
| --- | --- |
| Production MLOps (Feast, MLflow registry, A/B at scale) | Research POC; artifact is a local file + version string in Kafka headers. |
| Deep learning / LLM agents | Baseline uses scikit-learn (Random Forest or Gradient Boosting). |
| Flink SQL `ML_DETECT_ANOMALIES` | That path is anomaly detection, not supervised predictive maintenance; may be referenced in `notes.md` only. |
| Multi-region, authorization, exactly-once end-to-end | Local PLAINTEXT or minimal Confluent Cloud profile; EOS called out as deferred. |
| Fleet-wide federated learning | Single cluster, modest device count (3–10 reefers). |

---

## Flink SQL feature extraction

Implemented under [`flink/sql/`](flink/sql/): Kafka source on `reefer.telemetry.v1`, tumbling window on `event_ts`, `GROUP BY device_id`, sink to `reefer.features.v1`. See [`flink/README.md`](flink/README.md).

## Deferred (follow-ups)

| Topic | Notes |
| --- | --- |
| **Train from Flink features topic** | Python train reads flat JSON from `reefer.features.v1` instead of inline windowing. |
| **Confluent Flink** online learning / built-in ML functions | Compare to ARMA anomaly lab; document tradeoffs in `notes.md`. |
| **Model drift detection** | Population stability index on feature distributions; alert topic. |
| **Champion/challenger** | Two model versions scoring in parallel. |

---

## Architecture (logical)

![](./diagrams/context.drawio.png)

**Key idea:** `reefer.telemetry.v1` is the system of record for raw events. `reefer.features.v1` is optional but recommended so train/eval/score share identical feature definitions. If the POC stays minimal, features can be computed inline in each consumer; acceptance criteria allow either design (see scenarios).

---

## Event contracts

### Topic: `reefer.telemetry.v1`

- **Key:** `device_id` (string, e.g. `reefer_01`)
- **Value:** JSON (Avro/Protobuf deferred)
- **Compaction:** not compacted (append-only telemetry log)

#### Payload schema (required fields)

| Field | Type | Description |
| --- | --- | --- |
| `event_id` | string (UUID) | Idempotent dedup key |
| `device_id` | string | Reefer identifier |
| `event_time` | string (ISO-8601 UTC) | Event timestamp |
| `return_air_temp_c` | float | Return air temperature (°C) |
| `supply_air_temp_c` | float | Supply air temperature (°C) |
| `compressor_runtime_h` | float | Cumulative compressor hours |
| `door_open_count` | int | Door opens since last report (or cumulative per window) |
| `power_draw_kw` | float | Electrical load |
| `vibration_rms` | float | Optional mechanical stress proxy |
| `meta.split` | enum string | `train` \| `test` \| `inference` |
| `meta.is_labeled` | boolean | `true` for train/test; `false` for inference |
| `label.failure_class` | enum string \| null | `healthy` \| `degraded` \| `failure_imminent`; null when unlabeled |
| `label.horizon_hours` | int \| null | Prediction horizon used for label generation (e.g. 24) |

#### Label semantics (synthetic data)

The generator embeds failure physics in telemetry **before** the label horizon:

- **healthy** — temperatures in band, stable power, low vibration.
- **degraded** — gradual drift (rising return air, increasing power for same setpoint).
- **failure_imminent** — pattern within `horizon_hours` of a scripted failure event.

Train and test devices share the same schema; test devices must not appear in training rows (device-level holdout) **or** time-based split must be documented in `README.md` to prevent leakage.

### Topic: `reefer.features.v1` (recommended)

| Field | Type | Description |
| --- | --- | --- |
| `device_id` | string | Partition key |
| `window_start` / `window_end` | ISO-8601 | Window bounds |
| `feature_vector` | object | Named numeric features (see below) |
| `meta.split` | string | Copied from last event in window |
| `label.failure_class` | string \| null | Majority or last label in window for labeled splits |

**Baseline feature set** (per window, per device):

| Feature | Definition |
| --- | --- |
| `avg_return_air_temp_c` | Mean return air temperature |
| `std_return_air_temp_c` | Std dev return air |
| `delta_supply_return_c` | Mean(supply − return) |
| `slope_return_air_per_min` | Linear slope of return air vs time |
| `avg_power_draw_kw` | Mean power |
| `max_door_open_count` | Max door opens in window |
| `avg_vibration_rms` | Mean vibration |

### Topic: `reefer.ml.predictions.v1`

| Field | Type | Description |
| --- | --- | --- |
| `device_id` | string | |
| `scored_at` | ISO-8601 | Scoring timestamp |
| `model_version` | string | e.g. `v001` |
| `predicted_class` | string | Model output |
| `confidence` | float | Max class probability |
| `feature_ref` | object | Window id or feature snapshot hash |

### Topic: `reefer.ml.metrics.v1`

| Field | Type | Description |
| --- | --- | --- |
| `run_id` | string | Evaluation run |
| `model_version` | string | |
| `split` | string | Always `test` for offline eval from stream |
| `metrics` | object | `accuracy`, `precision`, `recall`, `f1`, per-class |
| `confusion_matrix` | array | Serialized counts |

---

## Split strategy (one topic, no leakage)

Records on `reefer.telemetry.v1` are interleaved by design. Separation rules:

| Rule | Implementation |
| --- | --- |
| **Metadata filter** | Consumers use `meta.split` — never assume topic name implies role. |
| **Device holdout** | `train`: `reefer_01`, `reefer_02`; `test`: `reefer_03` (example; configurable in generator config). |
| **Time ordering** | Generator emits train epoch, then test epoch, then inference; document order in README. |
| **No test in train** | Trainer commits offsets only for train filter; unit test asserts zero test `device_id` in training matrix. |

---

## Pinned stack

| Component | Version | Notes |
| --- | --- | --- |
| **Python** | 3.12+ | Managed with `uv` |
| **Kafka / CP** | 8.2.0+ | KRaft, `docker-compose.yaml` |
| **confluent-kafka** or **kafka-python** | latest compatible | Producer, consumer, admin |
| **scikit-learn** | 1.5+ | RandomForestClassifier or HistGradientBoostingClassifier |
| **pandas** / **numpy** | current | Feature matrices |
| **pytest** | current | TDD per [AGENTS.md](../AGENTS.md) |

Optional:

| Component | Version | Notes |
| --- | --- | --- |
| **Apache Kafka Streams** | 3.8+ / CP 8.2 | Java Maven module under `streams/` |
| **Confluent Cloud** | — | `.env.example` for API keys |

---

## Environment contract

- **Host:** Docker with published ports `9092` (broker), optional `8080` (optional REST/UI).
- **Project root:** `research/reefer-predictive-maintenance-kafka/`
- **Config:** `.env.example` for `BOOTSTRAP_SERVERS`, topic names, window size (default 60s), train/test device lists.
- **Artifacts:** `models/reefer_pm_{version}.joblib` gitignored; `models/.gitkeep` only.
- **Secrets:** No credentials in git; local `.env` only.

---

## Components (planned layout)

```
reefer-predictive-maintenance-kafka/
├── SPEC.md                 # this file
├── README.md               # runbook (after implementation)
├── notes.md                # session log
├── pyproject.toml          # uv project
├── docker-compose.yaml     # Kafka KRaft
├── .env.example
├── config/
│   └── generator.yaml      # devices, splits, failure schedules
├── src/reefer_pm_kafka/
│   ├── schema.py           # event validation
│   ├── generator.py        # synthetic telemetry → telemetry topic
│   ├── features.py         # windowed feature computation
│   ├── train.py            # consume train split, fit, save artifact
│   ├── evaluate.py         # consume test split, metrics topic
│   └── score.py            # consume inference split, predictions topic
├── tests/
│   ├── test_schema.py
│   ├── test_features.py
│   ├── test_split_filter.py
│   └── test_train_eval.py
└── streams/                # optional Java Kafka Streams (deferred)
```

CLI entry points (via `pyproject.toml` scripts):

- `reefer-pm-generate` — publish synthetic telemetry to `reefer.telemetry.v1`
- `reefer-pm-train` — train from stream (train split)
- `reefer-pm-evaluate` — evaluate on test split
- `reefer-pm-score` — run inference scorer

---

## Scenarios and acceptance

| # | Scenario | Accept when |
| --- | --- | --- |
| 1 | **Broker up** | `docker compose up` yields healthy Kafka; topics creatable. |
| 2 | **Unified telemetry** | Generator publishes train, test, and inference records to **one** topic; spot-check shows mixed `meta.split` on same topic. |
| 3 | **Schema validation** | Invalid records rejected or logged; unit tests cover required fields. |
| 4 | **Feature windows** | Per-device features match documented definitions for a fixed fixture stream. |
| 5 | **Train** | Trainer consumes only `meta.split=train`, writes `models/reefer_pm_v001.joblib` (or similar). |
| 6 | **Evaluate** | Evaluator consumes only `meta.split=test`, publishes metrics with F1 > 0.5 on synthetic data (threshold documents separability of synthetic labels). |
| 7 | **Score** | Scorer emits predictions for `meta.split=inference` with `model_version` set. |
| 8 | **Leakage test** | Automated test proves no test `device_id` rows in training feature matrix. |
| 9 | **Docs** | `README.md` describes one-topic design, run order, and comparison to separate train/test topics. |

---

## Execution order (demo script)

1. Start Kafka (`docker compose up -d`).
2. Create topics (script or `kafka-topics.sh`).
3. Run `reefer-pm-generate` until N train + M test + K inference events are produced (or run continuously with phase flags).
4. Run `reefer-pm-train` until training window buffer satisfies `min_samples` (configurable).
5. Run `reefer-pm-evaluate` on test portion (consumer may stop at end offsets for batch-style demo).
6. Run `reefer-pm-score` on inference traffic.
7. Inspect `reefer.ml.metrics.v1` and `reefer.ml.predictions.v1` with `kafka-console-consumer` or small inspect CLI.

---

## Model approach (baseline)

- **Task:** Multiclass classification — `healthy` / `degraded` / `failure_imminent`.
- **Algorithm:** `RandomForestClassifier` (interpretable, robust on tabular features) or `HistGradientBoostingClassifier` if class imbalance is high.
- **Input:** Windowed feature row per `device_id`.
- **Output:** Class + `predict_proba` max as confidence.
- **Minimum training samples:** 100 windows (configurable); demo generator must exceed this for train devices.

Future work may add survival analysis (time-to-failure) or regression on remaining useful life (RUL); out of scope for v1 acceptance.

---

## Risks and mitigations

| Risk | Mitigation |
| --- | --- |
| **Train/test leakage** | Device holdout + tests; document split in generator config. |
| **Class imbalance** | Stratified sampling in generator; `class_weight` in sklearn. |
| **Consumer offset confusion** | Separate `group.id` per stage: `reefer-pm-train`, `reefer-pm-eval`, `reefer-pm-score`. |
| **Feature drift** | Synthetic v1 only; deferred drift chapter. |
| **“Kafka Streams” vs Python consumers** | SPEC defines stream **pattern**; v1 implements Python stream consumers; Java KStreams optional in `streams/`. |

---

## Success metrics (research)

| Metric | Target (synthetic v1) |
| --- | --- |
| Test macro-F1 | ≥ 0.50 (sanity; raise as generator improves) |
| End-to-end latency (score) | < 5 s from event to prediction (local) |
| Lines of duplicated feature logic | 0 between train/eval/score (shared `features.py`) |

---

## Deliverables

| Artifact | Status |
| --- | --- |
| `SPEC.md` | This document |
| `README.md` | After implementation |
| `notes.md` | During research |
| `pyproject.toml` + `src/` + `tests/` | Implementation phase |
| `docker-compose.yaml` | Implementation phase |
| Update to [research/README.md](../README.md) | One paragraph link when POC runs |

---

## References

- Streaming ML train/test/inference on distinct logical streams — [ibm_notes.md](../../customers/project_notes/business/ibm_notes.md) (Paolo Patierno patterns).
- Reefer temperature streaming anomaly — [flink-studies 12-ai-agents](https://github.com/jbcodeforce/flink-studies/tree/master/code/flink-sql/12-ai-agents/).
- Agentic streaming context — [agentic_flink.md](../../flink-studies/docs/architecture/agentic_flink.md).
