"""Structured state objects shared between the research workflow agents.

These pydantic models are the contract between steps: the researcher emits a
:class:`ResearchPlan`, the coder emits a :class:`CodeResult`, the reporter
emits a :class:`PresentationResult`, and everything rolls up into a
:class:`ResearchRun`. Keeping them as typed schemas lets Agno re-serialize the
structured output of one step into the input of the next.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


def slugify(text: str) -> str:
    """Turn a human title into a filesystem/branch-friendly slug.

    Lower-cases, replaces non-alphanumeric runs with single hyphens, and
    strips leading/trailing hyphens.
    """
    slug = re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-")
    # Avoid an empty slug for non-alpha titles (e.g. "(research)").
    return slug or "research"


class ResearchPhase(str, Enum):
    """The sequential phases of a research investigation."""

    PLAN = "plan"
    SCAFFOLD = "scaffold"
    CODE = "code"
    PRESENT = "present"
    FINALIZE = "finalize"


class TechStack(BaseModel):
    """A single technology/stack choice with an optional rationale."""

    name: str
    reason: str = ""

    @field_validator("name")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("tech stack name must not be empty")
        return v


class FileSpec(BaseModel):
    """A file the harness intends to create, used to validate plan output."""

    path: str = Field(description="Relative to the project root, e.g. ./src/main.py")
    kind: str = "file"  # "file" or "dir"
    language: str = "python"


class ResearchPlan(BaseModel):
    """Structured plan produced by the researcher agent.

    Mirrors the per-research workflow from AGENTS.md: branch + top-level folder,
    a notes file, and a README report, plus a concrete file plan and tech stack.
    """

    topic: str
    folder_name: str = Field(description="Top-level folder name for this project")
    branch_name: str = Field(description="Git branch to run the research on")
    scope: str = Field(default="")
    hypothesis: str = Field(default="")
    success_criteria: str = Field(default="")
    tech_stack: List[TechStack] = Field(default_factory=list)
    files: List[FileSpec] = Field(default_factory=list)
    # Status string passed to the next workflow step.
    status: ResearchPhase = ResearchPhase.PLAN
    notes: str = ""

    @field_validator("folder_name", "branch_name")
    @classmethod
    def _not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError(f"field {v:20s} must not be empty")
        return v

    def relative_files(self) -> List[str]:
        """Return the file paths from the plan as a simple relative list."""
        return [f.path for f in self.files if f.kind == "file"]


class CodeResult(BaseModel):
    """Artifacts and observations produced by the coder agent."""

    src_files: List[FileSpec] = Field(default_factory=list)
    test_files: List[FileSpec] = Field(default_factory=list)
    run_command: Optional[str] = None
    observations: str = Field(default="")
    status: ResearchPhase = ResearchPhase.CODE
    notes: str = ""


class PresentationResult(BaseModel):
    """Markdown artefacts produced by the reporter agent."""

    notes_markdown: str = Field(default="")
    readme_markdown: str = Field(default="")
    root_readme_section: str = Field(default="")
    status: ResearchPhase = ResearchPhase.PRESENT
    notes: str = ""


class ResearchRun(BaseModel):
    """Rolls up the outcome of a whole research investigation."""
    research_name: str
    topic: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    plan: Optional[ResearchPlan] = None
    code: Optional[CodeResult] = None
    presentation: Optional[PresentationResult] = None
    git_commit_sha: Optional[str] = None
    notes: List[str] = Field(default_factory=list)
    project_path: Optional[Path] = None
    status: Optional[ResearchPhase] = None

    @property
    def folder_name(self) -> str:
        return self.plan.folder_name if self.plan else "research"

    @classmethod
    def from_topic(cls, name: str, topic: str) -> "ResearchRun":
        """Build an empty run."""
        return cls(research_name=name, topic=topic)

