# Research projects done with AI and me

This repository is strongly influenced by Simon Willison work, as I think it is cool to do code research, and studies independently of other repository on different subjects.

Each folder includes its own research project. I will use different Agents: Cursor, Claude Code, and custom ones done with Agno.

## [Apache Iceberg + Flink (Docker POC)](apache-iceberg-poc/README.md)
— local Flink 2.0, Iceberg REST catalog, MinIO; SQL scripts and quickstart-style flow.

## [Kafka consumer groups per topic & committed offsets](kafka-topic-consumer-offsets/README.md)
— Research-style **Python (uv)** tools (Admin API offset listing, demo consumer, `streams-demo-producer`) and a **Java Kafka Streams** sample (Maven) in [`kstream/`](kafka-topic-consumer-offsets/kstream/README.md); optional handoff walkthrough ([`streams-handoff/`](kafka-topic-consumer-offsets/streams-handoff/README.md): stop Streams, read offsets, Flink SQL `specific-offsets`); Confluent Cloud **or** local KRaft in `docker-compose.yaml`; notes vs `kafka-consumer-groups`.

## [Flink benchmark methodology and execution plan](flink-benchmark/README.md)
— Python-first benchmark research for Flink throughput, latency, scaling, and state backend trade-offs, with reproducible workload profiles (`W1`, `W2`, `W3`) and structured result artifacts.

## [Reefer predictive maintenance — Kafka stream ML](reefer-predictive-maintenance-kafka/README.md)
— Supervised failure prediction for reefers: training and test telemetry on one Kafka topic (`meta.split`), windowed features, sklearn classifier, local KRaft via Docker; see [SPEC.md](reefer-predictive-maintenance-kafka/SPEC.md).

## [Multi-tenant Debezium denormalizer PTF](flink-ptf-multitenant-debezium-spanout/README.md)
— Flink 2.2 ProcessTableFunction (same use case as DebeziumTransactionDenormalizer) that emits one order row per transaction with `line_items[]` and `tenant_id` for per-tenant routing; mock Debezium producer, local Docker, Confluent Cloud Flink; see [SPEC.md](flink-ptf-multitenant-debezium-spanout/SPEC.md).

## [Flink statement troubleshooting agent](flink-statement-troubleshooting/README.md)
— Agno Team CLI (`flink-triage`) for Confluent Cloud Flink SQL triage only; two-step flow (verify tooling → deploy on CC); perf-testing SQL fixture from flink-studies; see [DEPLOYMENT.md](flink-statement-troubleshooting/docs/DEPLOYMENT.md).

## [ksqlDB to Flink SQL migration skill](ksql-to-flink-skill/README.md)
— Portable agent skill and Agno/oMLX harness for ksqlDB → Confluent Cloud Flink SQL; fixtures from `flink_project_demos/ksql_tutorial`; see [SPEC.md](ksql-to-flink-skill/SPEC.md).

## [Spark SQL to Flink SQL migration skill](spark-to-flink-skill/README.md)
— Portable agent skill (`SKILL.md`) and Agno/oMLX harness for migrating Spark SQL to Confluent Cloud Flink SQL; golden pairs from `flink_project_demos/customer_360`; see [SPEC.md](spark-to-flink-skill/SPEC.md).

## [Flink skill harness common library](flink-skill-common/README.md)
— Shared Python package (`flink_skill_common`) used by the ksql-to-flink and spark-to-flink harnesses: output parsing, golden comparison, LLM config, MCP deploy, and Agno agent helpers.

## [Flink SQL aggregation state handoff](flink-sql-aggregation-state-handoff/README.md)
— Confluent Cloud study: user-operable aggregation handoff via upsert sink bootstrap + `specific-offsets` (savepoints not exposed to CC end users); stop global keyed aggregation, deploy new statement to `sink_v2` without full source replay; Python producer/validator, CC deploy script; see [SPEC.md](flink-sql-aggregation-state-handoff/SPEC.md) and [docs/PATTERNS.md](flink-sql-aggregation-state-handoff/docs/PATTERNS.md).

