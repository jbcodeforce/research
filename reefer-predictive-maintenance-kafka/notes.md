# Session notes — reefer predictive maintenance Kafka ML

## 2026-05-20 — Initial implementation

- Defined SPEC.md: single topic, metadata splits, device holdout.
- Implemented Python POC with `uv`, confluent-kafka, sklearn.
- Synthetic generator embeds failure physics (healthy → degraded → failure_imminent) per device timeline.
- Feature pipeline: 60s tumbling windows, seven numeric features, shared across train/eval/score.
- Separate consumer groups per ML stage read the same topic from earliest offset (batch demo mode).
- Offline tests validate no test device leakage into train features and macro-F1 ≥ 0.5 on synthetic data.
- Added `flink/sql/`: DDL source/sink + DML `TUMBLE` window grouped by `device_id`.
- Local variants (`*.local.sql`) use `127.0.0.1:9092`; `prepare_sql.sh` bundles scripts.
- SQL slope is min/max rate approximation; Python uses `polyfit` for `slope_return_air_per_min`.

## Open follow-ups

- Wire `reefer-pm-train` to consume Flink flat JSON from `reefer.features.v1`.
- Confluent Flink comparison (ARMA anomaly lab vs supervised PM).
- Java Kafka Streams module for feature extraction.
- Model drift detection on feature distributions.
