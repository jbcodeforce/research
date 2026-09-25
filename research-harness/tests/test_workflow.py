"""Tests for workflow parsing helpers: _content_of and _collect_structured."""

import pytest

from research_harness.state import CodeResult, PresentationResult, ResearchPlan, ResearchRun
from research_harness.workflow import _collect_structured, _content_of


class Stepish:
    """Minimal stand-in for an agno Workflow StepOutput with a ``content`` field."""

    def __init__(self, content):
        self.content = content


def test_content_of_none():
    assert _content_of(None) is None


def test_content_of_passthrough_string():
    assert _content_of("hello") == "hello"


def test_content_of_passthrough_dict_and_list():
    assert _content_of({"a": 1}) == {"a": 1}
    assert _content_of([1, 2]) == [1, 2]


def test_content_of_dumps_pydantic_model():
    model = ResearchPlan(topic="t", folder_name="f", branch_name="b")
    dumped = _content_of(model)
    assert isinstance(dumped, dict)
    assert dumped["topic"] == "t"


# ---------- _collect_structured ----------


def _step(text):
    return Stepish(content=text)


PLAN = '{"topic":"weather forecast","folder_name":"weather_forecast","branch_name":"weather_forecast","scope":"coding","status":"plan"}'
CODE = '{"src_files":[{"path":"src/app.py","code":"x"}],"test_files":[],"run_command":"uv run pytest","observations":"ok","status":"code"}'
PRES = '{"notes_markdown":"## Notes","readme_markdown":"## Presentation","root_readme_section":"idx","status":"present"}'


def test_collect_structured_parses_all_three_steps():
    run = ResearchRun.from_topic("weather forecast")
    run.project_path = None
    _collect_structured(run, [_step(PLAN), _step("scaffolded..."), _step(CODE), _step(PRES)])
    assert run.plan is not None and run.plan.topic == "weather forecast"
    assert run.plan.folder_name == "weather_forecast"
    assert run.code is not None and run.code.observations == "ok"
    assert run.presentation is not None and run.presentation.readme_markdown == "## Presentation"


def test_collect_structured_does_not_cross_wire_artifacts():
    # Even though CodeResult has no required fields, the presentation step must
    # still bind to presentation (not leak into code).
    run = ResearchRun.from_topic("weather forecast")
    run.project_path = None
    _collect_structured(run, [_step(PLAN), _step(CODE), _step(PRES)])
    assert run.plan.topic == "weather forecast"
    assert run.code.src_files[0].path == "src/app.py"
    assert run.presentation.root_readme_section == "idx"


def test_collect_structured_skips_non_json_steps():
    run = ResearchRun.from_topic("weather forecast")
    run.project_path = None
    _collect_structured(run, [_step("just a status string"), _step("no json here")])
    assert run.plan is None
    assert run.code is None
    assert run.presentation is None


def test_collect_structured_empty_results():
    run = ResearchRun.from_topic("weather forecast")
    run.project_path = None
    _collect_structured(run, [])
    assert run.plan is None
