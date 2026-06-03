"""Tests for CLI."""

from typer.testing import CliRunner

from flink_stmt_triage.cli.main import app

runner = CliRunner()


def test_cli_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


def test_run_dry_run():
    result = runner.invoke(
        app,
        [
            "run",
            "--statement",
            "perf-dml-passthrough",
            "--pool",
            "lfcp-test",
            "--dry-run",
        ],
    )
    assert result.exit_code == 0
    assert "perf-dml-passthrough" in result.stdout
    assert "RUNNING" in result.stdout


def test_tools_list():
    result = runner.invoke(app, ["tools", "list"])
    assert result.exit_code == 0
    assert "get_statement_status" in result.stdout


def test_status_dry_run_json():
    result = runner.invoke(
        app,
        ["status", "--statement", "s1", "--format", "json", "--dry-run"],
    )
    assert result.exit_code == 0
    assert "RUNNING" in result.stdout
