# Research projects done with AI and me

This repository is strongly influenced by Simon Willison work, as I think it is cool to do code research, and studies independently of other repository on different subjects.

Each folder includes its own research project. I will use different Agents: Cursor, Claude Code, and custom ones done with Agno.

## [Apache Iceberg + Flink (Docker POC)](apache-iceberg-poc/README.md)
— local Flink 2.0, Iceberg REST catalog, MinIO; SQL scripts and quickstart-style flow.

## [Kafka consumer groups per topic & committed offsets](kafka-topic-consumer-offsets/README.md)
— Research-style **Python (uv)** tools (Admin API offset listing, demo consumer, `streams-demo-producer`) and a **Java Kafka Streams** EOS sample (**Maven**) in [`kstream/`](kafka-topic-consumer-offsets/kstream/README.md); optional **handoff** walkthrough ([`streams-handoff/`](kafka-topic-consumer-offsets/streams-handoff/README.md): stop Streams, read offsets, Flink SQL `specific-offsets`); Confluent Cloud **or** local **KRaft** in `docker-compose.yaml`; notes vs `kafka-consumer-groups`.
