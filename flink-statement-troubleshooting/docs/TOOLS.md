# Tool surfaces for external agents

The core library in `flink_stmt_triage.tools` is agent-agnostic. Wire it into Hermes.ai, Claude Code, or Cursor using one of these surfaces.

## 1. Shell CLI (recommended)

All subcommands support `--format json` for machine-readable output.

```bash
uv run flink-triage run -s STATEMENT -p POOL [--dry-run]
uv run flink-triage status -s STATEMENT --format json
uv run flink-triage metrics -s STATEMENT -p POOL --format json
uv run flink-triage exceptions -s STATEMENT --format json
uv run flink-triage tools list
```

Generate schemas: `uv run flink-triage tools list` writes [`tools/schema.json`](../tools/schema.json).

## 2. Python import

```python
from flink_stmt_triage.tools import (
    get_statement_status,
    query_statement_metrics,
    run_triage,
    run_triage_dry_run,
)

report = run_triage_dry_run("perf-dml-passthrough", "lfcp-example")
```

## 3. Agno Team

```python
from flink_stmt_triage.agents.team import run_agno_triage

response = run_agno_triage("perf-dml-passthrough", "lfcp-xxxxx")
```

Or via CLI: `flink-triage run --use-agno`.

## 4. Confluent MCP

Install `@confluentinc/mcp-confluent` for IDE integration. Complements this project:

| MCP tool | This project's equivalent |
|----------|---------------------------|
| `read-flink-statement` | `flink-triage status` |
| `get-flink-statement-exceptions` | `flink-triage exceptions` |
| `query-metrics` | `flink-triage metrics` |
| `detect-flink-statement-issues` | `detect_statement_issues()` in tools |
| `get-flink-statement-profile` | Console / MCP (full task graph) |

## 5. Cursor skill

See [`skill/SKILL.md`](../skill/SKILL.md) for the interactive playbook.
