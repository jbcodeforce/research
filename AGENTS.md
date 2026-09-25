
## What this repository is

A monorepo of independent code-research projects (Simon Willison style): each top-level folder is a self-contained investigation into a data/streaming/ML topic, with no shared code between folders. There is no repo-wide build, test suite, or dependency graph — work happens *inside* one subproject at a time. `README.md` is the index of projects and their scope; keep it current (see workflow below).


## Per-research workflow

Each investigation follows the same lifecycle (from AGENTS.md):

1. Start by creating a branch from the main branch, select a short branch name for what the research is about:
    ```
    git checkout main
    git checkout <newbranch>
    ```
1. Start by creating a new top-level folder with a descriptive name.
2. Create a notes.md file in that folder and append notes to it as you work, tracking what you tried and anything you learned along the way
3. Write a `README.md` report at the end of the investigation.
4. Add any code to validate the research or deeper validate hypothesis. Prefer doing it in Python. Adopt test driven development in separate tests folderm and start by the unit tests for each important functions to implement. Do NOT include full copies of code that you fetched as part of your investigation
4. After finishing, add a section to the root `README.md` referencing the new project's intent and scope.
5. Commit only that folder plus the code/notes/README you produced.

## Tech stack conventions

- Python is the default for any code. Manage every Python project with `uv`.
- Test-driven: unit tests first, in a separate `tests/` folder. Refactor shared logic into common utilities rather than duplicating.
- Java projects use Maven (never Gradle).
- Confluent Platform images: version 8.2.0+ (community edition for Kafka). Apache Flink: 2.2+.
- Flink deployment preference: Confluent Cloud Flink managed via `dbt` + `dbt-confluent`
- Markdown: avoid heavy inline **bold** — it reads as AI-generated.
* When using Kafka use Confluent Platform community edition version 8.2.0 or above
* For Apache flink use version 2.4 and above.

## Coding

* Try to avoid duplicate function, refactor to reuse code as much as possible and isolate some functions in common utilities when necessary.
* comment functions with the intent.

### Python
* use `uv` for python project management
* Python subprojects share a layout: `src/<package>/` package, `tests/`, `pyproject.toml` (hatchling backend), console-script entry points under `[project.scripts]`, and pytest configured with `testpaths = ["tests"]`. Run commands from inside the subproject directory:

```bash
uv sync                              # install deps (add --extra dev where a dev extra exists)
uv run pytest                        # run the test suite
uv run pytest tests/test_x.py::test_y  # run a single test
uv run <console-script>              # e.g. reefer-pm-train, flink-triage, debezium-mock-produce
```

Each subproject's `[project.scripts]` block lists its runnable entry points — check `pyproject.toml` rather than guessing. Some declare a `dev` optional-dependency group (pytest/pytest-mock); others a `[dependency-groups]` dev group.

### Java
* for Java project use maven and not graddle.
* Maven (Java) subprojects — `kafka-topic-consumer-offsets/kstream/` and `flink-ptf-multitenant-debezium-spanout/ptf/`:

```bash
mvn -f <dir>/pom.xml package          # build; the PTF jar targets Flink 2.2.0
```

### Data Streaming Processing

Local infra: subprojects that need Kafka/Flink/Iceberg ship their own `docker-compose.yaml` — run `docker compose up -d` from that subproject. Confluent Cloud credentials and connection settings come from a local `.env` (loaded via `python-dotenv`); these files are not committed.

dbt-managed Flink SQL lives in `flink-ptf-multitenant-debezium-spanout/sql/order_pipeline/` (`dbt_project.yml`); run `dbt` commands from that directory.




