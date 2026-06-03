"""Typer CLI for flink-triage."""

from __future__ import annotations

import json
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from flink_stmt_triage.config import try_get_config
from flink_stmt_triage.triage_runner import execute_triage
from flink_stmt_triage.tools import TOOL_REGISTRY, run_triage_dry_run

app = typer.Typer(
    name="flink-triage",
    help="Confluent Cloud Flink statement troubleshooting tools and Agno team runner.",
    no_args_is_help=True,
)


class OutputFormat(str, Enum):
    text = "text"
    json = "json"


tools_app = typer.Typer(help="Tool introspection")
app.add_typer(tools_app, name="tools")


def _emit(data: object, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        typer.echo(json.dumps(data, indent=2, default=str))
    else:
        if isinstance(data, dict) and "summary" in data:
            from flink_stmt_triage.report import TriageReport

            typer.echo(TriageReport.model_validate(data).to_markdown())
        else:
            typer.echo(json.dumps(data, indent=2, default=str))


@app.command("run")
def run_cmd(
    statement: Annotated[str, typer.Option("--statement", "-s", help="Flink statement name")],
    pool: Annotated[str, typer.Option("--pool", "-p", help="Compute pool ID")],
    window: Annotated[int, typer.Option("--window", "-w", help="Metrics window (minutes)")] = 30,
    output: Annotated[
        Path | None, typer.Option("--output", "-o", help="Write markdown report to file")
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Use fixture data (no API calls)")
    ] = False,
    use_agno: Annotated[
        bool, typer.Option("--use-agno", help="Use Agno Team with LLM synthesis")
    ] = False,
    fmt: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.text,
) -> None:
    """Run full statement triage (deterministic or Agno team)."""
    if use_agno and not dry_run:
        if not try_get_config():
            typer.echo("Missing CC credentials for Agno triage. Set .env or use --dry-run.", err=True)
            raise typer.Exit(1)
        from flink_stmt_triage.agents.team import run_agno_triage

        response = run_agno_triage(statement, pool, window)
        content = getattr(response, "content", str(response))
        if output:
            output.write_text(content if isinstance(content, str) else str(content))
        typer.echo(content)
        return

    report = execute_triage(statement, pool, window_minutes=window, dry_run=dry_run)
    md = report.to_markdown()
    if output:
        output.write_text(md)
    if fmt == OutputFormat.json:
        _emit(report.model_dump(), OutputFormat.json)
    else:
        typer.echo(md)


@app.command("status")
def status_cmd(
    statement: Annotated[str, typer.Option("--statement", "-s")],
    fmt: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.json,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Get statement status."""
    if dry_run:
        from flink_stmt_triage.tools import load_fixture
        from flink_stmt_triage.flink_rest import statement_detail, statement_phase

        raw = load_fixture("statement_running.json")
        data = {
            "name": statement,
            "phase": statement_phase(raw),
            "detail": statement_detail(raw),
        }
    else:
        from flink_stmt_triage.tools import get_statement_status

        data = get_statement_status(statement)
    _emit(data, fmt)


@app.command("exceptions")
def exceptions_cmd(
    statement: Annotated[str, typer.Option("--statement", "-s")],
    fmt: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.json,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Get statement exceptions."""
    if dry_run:
        from flink_stmt_triage.tools import load_fixture

        data = load_fixture("exceptions_failed.json")
    else:
        from flink_stmt_triage.tools import get_statement_exceptions

        data = get_statement_exceptions(statement)
    _emit(data, fmt)


@app.command("metrics")
def metrics_cmd(
    statement: Annotated[str, typer.Option("--statement", "-s")],
    pool: Annotated[str, typer.Option("--pool", "-p")],
    window: Annotated[int, typer.Option("--window", "-w")] = 30,
    fmt: Annotated[OutputFormat, typer.Option("--format", "-f")] = OutputFormat.json,
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Query statement metrics snapshot."""
    if dry_run:
        data = run_triage_dry_run(statement, pool)
        data = {k: v for k, v in data.items() if k == "metrics"}
    else:
        from flink_stmt_triage.tools import query_statement_metrics

        data = query_statement_metrics(statement, pool, window)
    _emit(data, fmt)


@tools_app.command("list")
def tools_list() -> None:
    """Print tool names and parameter hints as JSON schemas."""
    schemas = []
    for name, fn in TOOL_REGISTRY.items():
        doc = (fn.__doc__ or "").strip().split("\n")[0]
        schemas.append({"name": name, "description": doc})
    out_path = Path(__file__).resolve().parents[3] / "tools" / "schema.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(schemas, indent=2) + "\n")
    typer.echo(json.dumps(schemas, indent=2))


def main() -> None:
    app()


if __name__ == "__main__":
    main()
