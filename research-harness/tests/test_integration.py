"""End-to-end integration test: run the full workflow offline with a stub model.

Verifies the researcher -> scaffold -> coder -> reporter -> finalize pipeline
produces a git branch, writes the project README/notes, updates the root
README section, and is deterministic -- all without any LLM or network access.
"""

import json
import subprocess

from research_harness.config import LLMConfig, ProjectConfig, RepoConventions
from research_harness.state import ResearchPhase, ResearchRun
from research_harness.tools.stub import SequenceModel
from research_harness import workflow

PLAN_JSON = (
    '{"topic":"weather forecast llm",'
    '"folder_name":"weather_forecast",'
    '"branch_name":"research-weather-forecast-llm",'
    '"scope":"coding","hypothesis":"llm can forecast",'
    '"status":"plan"}'
)
CODE_JSON = (
    '{"src_files":[{"path":"src/app.py","code":"print(1)"}],'
    '"test_files":[{"path":"test_app.py","code":"pass"}],'
    '"run_command":"uv run pytest","observations":"tests green","status":"code"}'
)
PRES_JSON = (
    '{"notes_markdown":"## Notes\\ncontent",'
    '"readme_markdown":"## Presentation\\nsummary",'
    '"root_readme_section":"## weather forecast llm",'
    '"status":"present"}'
)


def _init_git_repo(path):
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(path))
    subprocess.run(["git", "config", "user.name", "Test"], cwd=str(path))
    return path


def _make_config(tmp_path):
    _init_git_repo(tmp_path)
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    pcfg = ProjectConfig(
        research_name="wf",
        repo_root=repo_root,
        git_root=repo_root,
        llm=LLMConfig(),
        conventions=RepoConventions(),
        project_path=repo_root / "wf",
    )
    return pcfg


def test_run_research_offline_end_to_end(tmp_path):
    config = _make_config(tmp_path)
    model = SequenceModel([PLAN_JSON, CODE_JSON, PRES_JSON])
    run = workflow.run_research("weather forecast llm", config, model=model)

    # Full pipeline reached finalize, deterministically.
    assert run.status == ResearchPhase.FINALIZE

    # Structured artefacts parsed correctly.
    assert run.plan is not None
    assert run.plan.topic == "weather forecast llm"
    assert run.plan.folder_name == "weather_forecast"
    assert run.code is not None
    assert run.code.src_files[0].path == "src/app.py"
    assert run.code.observations == "tests green"
    assert run.presentation is not None
    assert run.presentation.readme_markdown == "## Presentation\nsummary"

    # A git branch and commit were created on the branch.
    assert run.git_commit_sha
    current = subprocess.run(
        ["git", "-C", str(config.git_root), "branch", "--show-current"],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert current == run.plan.branch_name

    # Project deliverables written.
    project_readme = config.project_path / "README.md"
    notes = config.project_path / "notes.md"
    assert project_readme.exists()
    assert notes.exists()
    assert "weather forecast llm" in project_readme.read_text()
    assert "notes: weather forecast llm" in notes.read_text()

    # Root README index updated (and NOT clobbering the project README).
    root_readme = config.repo_root / "README.md"
    assert root_readme.exists()
    assert "weather forecast llm" in root_readme.read_text()


def test_run_research_returns_research_run(tmp_path):
    config = _make_config(tmp_path)
    model = SequenceModel([PLAN_JSON, CODE_JSON, PRES_JSON])
    run = workflow.run_research("weather forecast llm", config, model=model)
    assert isinstance(run, ResearchRun)


def test_pres_json_is_valid_json():
    obj = json.loads(PRES_JSON)
    assert set(obj) == {"notes_markdown", "readme_markdown", "root_readme_section", "status"}
