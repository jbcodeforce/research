# Investigation notes

## 2026-06-02 — Project start

- Agno Team CLI + reusable tools for CC Flink statement triage.
- Debug fixture: perf-testing SQL from flink-studies on Confluent Cloud Kafka.
- Scope: Confluent Cloud only (no local or K8s Flink runtime).

## 2026-06-02 — Implementation

- Step 1: `step1_verify.sh` — pytest + dry-run (no cluster)
- Step 2: `step2_deploy_cc.sh` — deploy CC Flink statements + live triage
- Removed K8s/OSS Flink assets (out of scope)
