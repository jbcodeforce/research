"""Tests for typer CLI in research_harness.research_cli."""
from __future__ import annotations

from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from research_harness.research_cli import app, main
from research_harness.state import ResearchPhase, ResearchPlan, ResearchRun

runner = CliRunner()


def test_cli_help():
    """Verify that --help works and shows options."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "research" in result.stdout.lower() or "run" in result.stdout.lower()


def test_cli_run_direct(tmp_path):
    """Test calling the CLI with topic invokes run_research and outputs summary."""
    mock_run = ResearchRun(
        research_name= "rtest",
        topic="test topic",
        status=ResearchPhase.FINALIZE,
        project_path=tmp_path / "test-topic",
        plan=ResearchPlan(topic="test topic", folder_name="test-topic", branch_name="research-test-topic"),
        git_commit_sha="abcdef1234567890",
    )
    with patch("research_harness.research_cli.run_research", return_value=mock_run) as mock_fn:
        result = runner.invoke(
            app,
            [
                "rtest",
                "test topic",
                "--repo-root",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert mock_fn.called
        args, kwargs = mock_fn.call_args
        assert args[0] == "test topic"
        pcfg = args[1]
        assert pcfg.repo_root == tmp_path.resolve()
        assert "research-test-topic" in result.stdout
        assert "abcdef1234567890" in result.stdout
        assert "Research workflow completed: finalize" in result.stdout


def test_cli_main_callable():
    """Verify main() function executes without error when invoking --help."""
    with patch("sys.argv", ["research", "--help"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0
