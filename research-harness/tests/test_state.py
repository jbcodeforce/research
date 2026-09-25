"""Tests for structured state: slugify, validation, and model helpers."""

import pytest

from research_harness.state import (
    CodeResult,
    FileSpec,
    ResearchPlan,
    ResearchPhase,
    TechStack,
    slugify,
)


def test_slugify_basic():
    assert slugify("Neural Weather Forecasting") == "neural-weather-forecasting"


def test_slugify_collapses_separators():
    assert slugify("a   b\tc") == "a-b-c"


def test_slugify_falls_back_for_parentheses_title():
    # "(research)" has no alphanumerics -> empty slug -> "research"
    assert slugify("(research)") == "research"


def test_slugify_ignores_uppercase_and_digits_kept():
    assert slugify("LLM-7") == "llm-7"


def test_research_plan_requires_topic_folder_branch():
    with pytest.raises(Exception):
        ResearchPlan(topic="")  # required fields missing
    with pytest.raises(Exception):
        ResearchPlan(topic="x", folder_name="   ", branch_name="b")


def test_research_plan_rejects_empty_folder_or_branch():
    # provided but whitespace -> validator rejects
    with pytest.raises(Exception):
        ResearchPlan(topic="x", folder_name="  ", branch_name="b")


def test_research_plan_defaults():
    plan = ResearchPlan(topic="hello world", folder_name="hello-world", branch_name="research-hello-world")
    assert plan.scope == ""
    assert plan.tech_stack == []
    assert plan.files == []
    assert plan.status == ResearchPhase.PLAN
    assert plan.notes == ""


def test_research_plan_relative_files_filters_dirs():
    plan = ResearchPlan(
        topic="t",
        folder_name="f",
        branch_name="b",
        files=[
            FileSpec(path="./src/app.py", kind="file"),
            FileSpec(path="./src", kind="dir"),
            FileSpec(path="./docs/readme.md", kind="file"),
        ],
    )
    assert plan.relative_files() == ["./src/app.py", "./docs/readme.md"]


def test_tech_stack_requires_name():
    with pytest.raises(Exception):
        TechStack(name="")


def test_tech_stack_coerces_dict():
    ts = TechStack.model_validate({"name": "pydantic", "reason": "fast"})
    assert ts.name == "pydantic"
    assert ts.reason == "fast"


def test_codespec_coerces_dict():
    fs = FileSpec.model_validate({"path": "src/app.py"})
    assert fs.path == "src/app.py"
    assert fs.kind == "file"


def test_code_result_parses_nested_filespec():
    result = CodeResult.model_validate(
        {
            "src_files": [{"path": "src/app.py", "code": "def x(): pass"}],
            "test_files": [],
            "run_command": "uv run pytest",
            "observations": "all passed",
            "status": "code",
        }
    )
    assert result.observations == "all passed"
    assert result.src_files[0].path == "src/app.py"
    assert result.run_command == "uv run pytest"
