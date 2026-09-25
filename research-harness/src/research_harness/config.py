"""Harness configuration: repository root, LLM settings and repo conventions.

This module is intentionally free of any LLM or filesystem side effects so it
can be imported and unit tested without network access or API keys.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

from dotenv import dotenv_values


@dataclass
class LLMConfig:
    """OpenAI-compatible model settings.

    Works with any OpenAI-compatible endpoint, including local providers such
    as OMLX or Ollama. All values fall back to environment variables.
    """

    base_url: str = "http://127.0.0.1:7999/v1"
    model_id: str = "Ornith-1.5-9B-MLX-8bit"
    api_key: Optional[str] = None
    temperature: float = 0.0
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.getenv("RESEARCH_LLM_BASE_URL", os.getenv("LLM_URL", "http://127.0.0.1:7999/v1")),
            model_id=os.getenv("RESEARCH_LLM_MODEL", os.getenv("LLM_MODEL", "Ornith-1.5-9B-MLX-8bit")),
            api_key=os.getenv("OPENAI_API_KEY"),  # None disables auth (e.g. OMLX)
            temperature=float(os.getenv("RESEARCH_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("RESEARCH_LLM_MAX_TOKENS", "4096")),
        )


@dataclass
class RepoConventions:
    """Naming and process conventions copied from this repo's AGENTS.md."""

    git_branch_prefix: str = "research-"
    git_commit_message: str = "research: <topic>"
    notes_filename: str = "notes.md"
    readme_filename: str = "README.md"
    code_fence_language: str = "python"
    default_tool: str = "uv"
    test_command: str = "pytest"


@dataclass
class HarnessConfig:
    """Top-level configuration for a research run."""

    repo_root: Path
    git_root: Optional[Path] = None
    llm: LLMConfig = field(default_factory=LLMConfig)
    conventions: RepoConventions = field(default_factory=RepoConventions)
    dry_run: bool = False

    @property
    def root(self) -> Path:
        """The root of the research project folder (repo_root/<slug>).</"""
        return self.repo_root


@dataclass
class ProjectConfig(HarnessConfig):
    """Configuration bound to a specific (already scaffolded) project folder."""

    project_path: Path = Path(".")


def load_config_from_env() -> LLMConfig:
    """Build :class:`LLMConfig` from the first ``.env`` file found up the tree."""
    loader = os.path.dirname(os.path.abspath(__file__))
    project_dir = Path(loader).resolve().parent
    for candidate in [project_dir, project_dir.parent]:
        values = dotenv_values(str(candidate / ".env"))
        if values:
            return LLMConfig(
                base_url=values.get("LLM_URL", values.get("RESEARCH_LLM_BASE_URL", "http://127.0.0.1:11434/v1")),
                model_id=values.get("LLM_MODEL", values.get("RESEARCH_LLM_MODEL", "qwen2.5:latest")),
                api_key=values.get("OPENAI_API_KEY"),
                temperature=float(values.get("RESEARCH_LLM_TEMPERATURE", "0.0")),
                max_tokens=int(values.get("RESEARCH_LLM_MAX_TOKENS", "4096")),
            )
    return LLMConfig.from_env()
