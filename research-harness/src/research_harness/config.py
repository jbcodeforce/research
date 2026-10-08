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
    api_key: Optional[str] = "local-key"
    temperature: float = 0.0
    max_tokens: int = 4096

    @classmethod
    def from_env(cls) -> "LLMConfig":
        return cls(
            base_url=os.getenv("RESEARCH_LLM_BASE_URL", os.getenv("LLM_URL", "http://127.0.0.1:7999/v1")),
            model_id=os.getenv("RESEARCH_LLM_MODEL", os.getenv("LLM_MODEL", "Ornith-1.5-9B-MLX-8bit")),
            api_key=os.getenv("LLM_API_KEY"),
            temperature=float(os.getenv("RESEARCH_LLM_TEMPERATURE", "0.0")),
            max_tokens=int(os.getenv("RESEARCH_LLM_MAX_TOKENS", "4096")),
        )


@dataclass
class RepoConventions:
    """Naming and process conventions copied from this repo's AGENTS.md."""

    git_branch_prefix: str = "rearcher-"
    git_commit_message: str = "research: <topic>"
    notes_filename: str = "notes.md"
    readme_filename: str = "README.md"
    code_fence_language: str = "python"
    default_tool: str = "uv"
    test_command: str = "pytest"


@dataclass
class HarnessConfig:
    """Top-level configuration for a research run."""
    research_name: str
    repo_root: Path
    git_root: Optional[Path] = None
    llm: LLMConfig = field(default_factory=LLMConfig)
    conventions: RepoConventions = field(default_factory=RepoConventions)

    @property
    def root(self) -> Path:
        """The root of the research project folder (repo_root/<slug>).</"""
        return self.repo_root


@dataclass
class ProjectConfig(HarnessConfig):
    """Configuration bound to a specific (already scaffolded) project folder."""

    project_path: Path = Path(".")


def load_config_from_env(cwd: Optional[Path] = None) -> LLMConfig:
    """Build :class:`LLMConfig` from the first ``.env`` file from DOT_ENV_FILE  or found up the tree.

    Searches ``cwd`` (defaults to the caller's working directory), then the
    package directory tree. Loads the found file into ``os.environ`` via
    ``load_dotenv`` so that downstream libraries (agno, OpenAI client) that
    read environment variables directly will also pick up the values.
    """
    from dotenv import load_dotenv
    # Load .env file specified by DOT_ENV_FILE if it exists
    dot_env_file = os.environ.get("DOT_ENV_FILE")
    if dot_env_file and Path(dot_env_file).is_file():
        load_dotenv(dot_env_file, override=False)
    else:
        search_dirs = []
        if cwd is not None:
            search_dirs.append(cwd.resolve())
        loader = os.path.dirname(os.path.abspath(__file__))
        project_dir = Path(loader).resolve().parent
        search_dirs += [project_dir, project_dir.parent]

        for candidate in search_dirs:
            dot_env_file = candidate / ".env"
            if dot_env_file.is_file():
                load_dotenv(str(dot_env_file), override=False)
                break
    values = dotenv_values(str(dot_env_file))
    return LLMConfig(
        base_url=values.get("LLM_URL") or values.get("RESEARCH_LLM_BASE_URL") or "http://127.0.0.1:11434/v1",
        model_id=values.get("LLM_MODEL") or values.get("RESEARCH_LLM_MODEL") or "qwen2.5:latest",
        api_key=values.get("LLM_API_KEY"),
        temperature=float(values.get("RESEARCH_LLM_TEMPERATURE") or "0.0"),
        max_tokens=int(values.get("RESEARCH_LLM_MAX_TOKENS") or "4096"),
    )

