"""Typer CLI interface for the agentic research harness.

Provides a CLI to trigger the multi-agent research workflow on a topic,
loading settings and credentials from .env.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from research_harness.config import (
    ProjectConfig,
    RepoConventions,
    load_config_from_env,
)
from research_harness.state import slugify
from research_harness.workflow import run_research

app = typer.Typer(
    help="Agentic research harness: run research investigations following AGENTS.md conventions.",
    no_args_is_help=True,
)


@app.command()
def run(
    name: str = typer.Argument(
        ...,
        help="Research name",
    ),
    topic: str = typer.Argument(
        ...,
        help="Research topic or question to investigate",
    ),
    repo_root: Optional[Path] = typer.Option(
        None,
        "--repo-root",
        "-r",
        help="Path to repository root (defaults to current working directory)",
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Dry run mode without LLM calls or filesystem side effects",
    ),
) -> None:
    """Run the multi-agent research workflow on a topic."""
    resolved_root = repo_root.resolve() if repo_root else Path.cwd().resolve()
    llm_cfg = load_config_from_env(cwd=resolved_root)
    conventions = RepoConventions()
    project_slug = f"{slugify(name)}"
    target_project_path = resolved_root / project_slug

    pcfg = ProjectConfig(
        research_name=name,
        repo_root=resolved_root,
        git_root=resolved_root,
        llm=llm_cfg,
        conventions=conventions,
        dry_run=dry_run,
        project_path=target_project_path
    )

    typer.echo(f"Starting research workflow for: {topic}")
    typer.echo(f"Target folder: {target_project_path}")
    typer.echo(f"Model: {llm_cfg.model_id} @ {llm_cfg.base_url}")

    try:
        run_result = run_research(topic, pcfg)
    except Exception as exc:
        msg = str(exc)
        # Detect the two most common failure modes and give a clear fix hint.
        if "connection" in msg.lower() or "connect" in msg.lower():
            typer.echo(
                f"\nERROR: Could not reach the LLM endpoint at {llm_cfg.base_url}\n"
                f"  Check that the model server is running and the URL is correct.\n"
                f"  Set LLM_URL in your .env to override (current: {llm_cfg.base_url})",
                err=True,
            )
        elif "api_key" in msg.lower() or "authentication" in msg.lower() or "unauthorized" in msg.lower():
            typer.echo(
                "\nERROR: LLM authentication failed.\n"
                "  Set LLM_API_KEY in your .env file.",
                err=True,
            )
        else:
            typer.echo(f"\nERROR: {exc}", err=True)
        raise typer.Exit(code=1) from None

    status_str = run_result.status.value if run_result.status else "completed"
    typer.echo(f"\nResearch workflow completed: {status_str}")
    if run_result.plan:
        typer.echo(f"Branch: {run_result.plan.branch_name}")
        typer.echo(f"Folder: {run_result.plan.folder_name}")
    if run_result.git_commit_sha:
        typer.echo(f"Commit SHA: {run_result.git_commit_sha}")
    if run_result.project_path:
        typer.echo(f"Outputs written to: {run_result.project_path}")


def main() -> None:
    """Entry point for console scripts."""
    app()


if __name__ == "__main__":
    main()
