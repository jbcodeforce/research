# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repository is

A monorepo of independent code-research projects (Simon Willison style): each top-level folder is a self-contained investigation into a data/streaming/ML topic, with no shared code between folders. There is no repo-wide build, test suite, or dependency graph — work happens *inside* one subproject at a time. `README.md` is the index of projects and their scope; keep it current (see workflow below).

`AGENTS.md` is the authoritative source for working conventions (code style, product versions, Flink deployment preferences, markdown rules). Read it before starting work — the points below summarize the operational parts, but AGENTS.md governs.

## Per-research workflow

Each investigation follows the same lifecycle (from AGENTS.md):

1. Create a new top-level folder with a descriptive name.
2. Keep a `notes.md` in it, appended to as you work — what you tried and what you learned.
3. Write a `README.md` report at the end of the investigation.
4. After finishing, add a section to the root `README.md` referencing the new project's intent and scope.
5. Commit only that folder plus the code/notes/README you produced.

## Tech stack conventions

- Python is the default for any code. Manage every Python project with `uv`.
- Test-driven: unit tests first, in a separate `tests/` folder. Refactor shared logic into common utilities rather than duplicating.
- Java projects use Maven (never Gradle).
- Confluent Platform images: version 8.2.0+ (community edition for Kafka). Apache Flink: 2.2+.
- Flink deployment preference: Confluent Cloud Flink managed via `dbt` + `dbt-confluent`; Apache Flink OSS is the fallback.
- Markdown: avoid heavy inline **bold** — it reads as AI-generated.

## Common commands

Python subprojects share a layout: `src/<package>/` package, `tests/`, `pyproject.toml` (hatchling backend), console-script entry points under `[project.scripts]`, and pytest configured with `testpaths = ["tests"]`. Run commands from inside the subproject directory:

```bash
uv sync                              # install deps (add --extra dev where a dev extra exists)
uv run pytest                        # run the test suite
uv run pytest tests/test_x.py::test_y  # run a single test
uv run <console-script>              # e.g. reefer-pm-train, flink-triage, debezium-mock-produce
```

Each subproject's `[project.scripts]` block lists its runnable entry points — check `pyproject.toml` rather than guessing. Some declare a `dev` optional-dependency group (pytest/pytest-mock); others a `[dependency-groups]` dev group.

Maven (Java) subprojects — `kafka-topic-consumer-offsets/kstream/` and `flink-ptf-multitenant-debezium-spanout/ptf/`:

```bash
mvn -f <dir>/pom.xml package          # build; the PTF jar targets Flink 2.2.0
```

Local infra: subprojects that need Kafka/Flink/Iceberg ship their own `docker-compose.yaml` — run `docker compose up -d` from that subproject. Confluent Cloud credentials and connection settings come from a local `.env` (loaded via `python-dotenv`); these files are not committed.

dbt-managed Flink SQL lives in `flink-ptf-multitenant-debezium-spanout/sql/order_pipeline/` (`dbt_project.yml`); run `dbt` commands from that directory.

## Subprojects (see root README.md for full scope)

- `apache-iceberg-poc/` — local Flink 2.0 + Iceberg REST catalog + MinIO, SQL-driven POC.
- `kafka-topic-consumer-offsets/` — Python (uv) Admin-API offset tooling + a Java Kafka Streams sample in `kstream/`.
- `flink-benchmark/` — Python-first Flink throughput/latency/scaling benchmark methodology.
- `reefer-predictive-maintenance-kafka/` — supervised reefer-failure prediction over one Kafka telemetry topic (sklearn).
- `flink-ptf-multitenant-debezium-spanout/` — Flink 2.2 ProcessTableFunction (Java/Maven) + mock Debezium producer (Python) + dbt SQL pipeline.
- `flink-statement-troubleshooting/` — Agno Team CLI (`flink-triage`) for Confluent Cloud Flink SQL triage.
- `flink-sql-aggregation-state-handoff/` — Confluent Cloud study of user-operable aggregation state handoff via upsert bootstrap + `specific-offsets`.
- `fine-tuning-llm/` — fine-tuning an LLM for Spark→Flink SQL migration (PEFT/TRL/transformers).
