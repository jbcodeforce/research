# Research projects done with AI and me

This repository is strongly influenced by Simon Willison work, as I think it is cool to do code research, and studies independently of other repository on different subjects.

Each folder includes its own research project. I will use different Agents: Cursor, Claude Code, and custom ones done with Agno.

## [Apache Iceberg + Flink (Docker POC)](apache-iceberg-poc/README.md)
— local Flink 2.0, Iceberg REST catalog, MinIO; SQL scripts and quickstart-style flow.

## [Kafka consumer groups per topic & committed offsets](kafka-topic-consumer-offsets/README.md)
— Research-style **Python (uv)** utilities: discover consumer groups **per topic** and **committed offsets** via the Admin API (Confluent Cloud **or** local **KRaft** in `docker-compose.yaml`), plus a demo consumer and notes vs `kafka-consumer-groups`.
