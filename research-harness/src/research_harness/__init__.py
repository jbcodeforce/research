"""Agentic research harness: an Agno workflow for doing research in this repo."""

from research_harness.config import (
    HarnessConfig,
    LLMConfig,
    ProjectConfig,
    RepoConventions,
)
from research_harness.state import (
    CodeResult,
    PresentationResult,
    ResearchPhase,
    ResearchPlan,
    ResearchRun,
    slugify,
)
from research_harness.tools.markdown import code, code_block, heading, link, table
from research_harness.tools.repo import (
    create_branch,
    current_branch,
    git_commit,
    list_projects,
    read_agents_md,
    write_file,
)
from research_harness.workflow import build_default_plan

__version__ = "0.1.0"

__all__ = [
    "HarnessConfig",
    "LLMConfig",
    "RepoConventions",
    "ProjectConfig",
    "ResearchPhase",
    "ResearchPlan",
    "ResearchRun",
    "CodeResult",
    "PresentationResult",
    "build_default_plan",
    "slugify",
    "code",
    "code_block",
    "heading",
    "link",
    "table",
    "write_file",
    "list_projects",
    "read_agents_md",
    "create_branch",
    "git_commit",
    "current_branch",
]
