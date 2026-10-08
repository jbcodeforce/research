"""The Agno multi-agent research workflow.

A sequential ``agno.Workflow`` of three LLM agents (researcher -> coder ->
reporter) interleaved with one deterministic step (scaffold). Content flows from
step to step: the researcher's JSON plan is the coder's input, and so on. The
deterministic runner re-parses the structured step outputs into typed models,
materializes the final markdown deliverables and commits them.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agno.agent import Agent
from agno.models.base import Model
from agno.workflow import Step, StepInput, Workflow

from research_harness.agents.coder import build_coder
from research_harness.agents.factory import build_model
from research_harness.agents.reporter import build_reporter
from research_harness.agents.researcher import build_researcher
from research_harness.config import HarnessConfig, ProjectConfig
from research_harness.extract import model_from_json, find_json
from research_harness.present import (
    build_notes,
    build_readme,
    build_root_readme_section,
)
from research_harness.state import (
    CodeResult,
    PresentationResult,
    ResearchPhase,
    ResearchPlan,
    ResearchRun,
)
from research_harness.tools import repo, run_shell

_MIN_STEP_KEYS = 3


def _content_of(content: Any) -> Any:
    if content is None:
        return None
    if isinstance(content, (dict, list)):
        return content
    if hasattr(content, "model_dump"):
        return content.model_dump()
    return content


def _scaffold_executor(step_input: StepInput, project_path: Path, git_root: Path) -> str:
    """Deterministic step: create the git branch and empty project folder.

    Reads the researcher's plan JSON from ``previous_step_content``.
    """
    plan = model_from_json(ResearchPlan, step_input.previous_step_content)
    if plan is None:
        plan = model_from_json(ResearchPlan, step_input.input)
    if plan is None:
        return "scaffold: no plan found"
    repo.create_branch(git_root, plan.branch_name)
    repo.ensure_folder(".", project_path)
    return f"scaffolded {plan.folder_name} on branch '{plan.branch_name}'"



def _build_research_workflow(config: HarnessConfig, topic: str) -> Workflow:
    """Assemble the Agno research workflow for ``topic``."""
    project_path = config.project_path
    git_root = config.git_root or project_path
    model = build_model(config)
    researcher = build_researcher(model, project_path, topic=topic)
    coder = build_coder(model, project_path, topic=topic)
    reporter = build_reporter(model, project_path, topic=topic)

    scaffold = Step(
        name="scaffold",
        executor=lambda step_input: _scaffold_executor(step_input, project_path, git_root),
    )

    return Workflow(
        name="research_workflow",
        steps=[
            Step(name="plan", agent=researcher),
            scaffold,
            Step(name="code", agent=coder),
            Step(name="present", agent=reporter),
        ],
    )


def _finalize(run: ResearchRun, project_path: Path, git_root: Path, conventions) -> str:
    """Write the final markdown deliverables and commit them on the branch."""
    if run.presentation is None or run.plan is None:
        return "finalize: missing artefacts"
    root = project_path
    repo.ensure_folder(".", root)
    readme_md = build_readme(run.plan, run.code or CodeResult(), run.presentation)
    notes_md = build_notes(run.plan, run.code or CodeResult(), run.presentation)
    repo.write_file(root, "README.md", readme_md)
    repo.write_file(root, "notes.md", notes_md)
    section = build_root_readme_section(run.plan, run.code or CodeResult(), run.presentation)
    repo.write_file(git_root, "README.md", section + "\n")
    repo.git_add(root, ["README.md", "notes.md"])
    sha = repo.git_commit(run.project_path, f"research: {run.topic}")
    run.git_commit_sha = sha
    return f"committed {sha}"


def _collect_structured(run: ResearchRun, step_results) -> None:
    """Parse JSON step outputs into ``run.plan`` / ``run.code`` / ``run.presentation``.

    Each step's text is matched to the schema with the most of its declared field
    names present in the JSON (requiring at least ``_MIN_STEP_KEYS``). This lets a
    partial schema still match, while preventing a schema with no required fields
    (e.g. CodeResult) from matching the wrong artefact.
    """
    schemas = [(ResearchPlan, "plan"), (CodeResult, "code"), (PresentationResult, "presentation")]
    for item in step_results or []:
        if item is None:
            continue
        content = _content_of(getattr(item, "content", item))
        data = find_json(content) if content is not None else None
        if not isinstance(data, dict):
            continue
        best_cls, best_name, best_count = None, None, 0
        for model_cls, _field_name in schemas:
            overlap = sum(1 for name in model_cls.model_fields if name in data)
            if overlap > best_count:
                best_count, best_cls, best_name = overlap, model_cls, _field_name
        if best_cls is None or best_count < _MIN_STEP_KEYS:
            continue
        parsed = model_from_json(best_cls, content)
        if parsed is not None:
            setattr(run, best_name, parsed)


def run_research(topic: str, config: ProjectConfig, model: Optional[Model] = None) -> ResearchRun:
    """Run the full research workflow and assemble a :class:`ResearchRun`.
    The research workflow executes different agents. The state is modeled in ResearchPlan.
    """
    git_root = config.git_root or config.project_path
    run = ResearchRun.from_topic(config.research_name, topic)
    run.project_path = config.project_path
    run.plan = _build_default_plan(run, config.conventions)
    run.status = ResearchPhase.PLAN

    workflow = _build_research_workflow(config, topic)
    out = workflow.run(input=topic)
    _collect_structured(run, out.step_results)
    run.status = ResearchPhase.CODE
    _finalize(run, config.project_path, git_root, config.conventions)
    run.status = ResearchPhase.FINALIZE
    return run


def _build_default_plan(run: ResearchRun, conventions) -> ResearchPlan:
    """Create a default plan with folder/branch names derived from the topic."""
    from research_harness.state import slugify

    slug = f"{conventions.git_branch_prefix}{slugify(run.research_name)}"
    return ResearchPlan(topic=run.topic, folder_name=slug, branch_name=slug)
