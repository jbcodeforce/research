"""Tool callables exposed to the research agents.

agno wraps each tool and calls it with the arguments the agent passes. This
module binds the project root once (via :func:`functools.partial`) and returns
the full tool list for an agent.
"""

from __future__ import annotations

from functools import partial
from pathlib import Path

from research_harness.tools import repo, run_shell


def _bind_tools(project_path: Path) -> list:
    """Return the full tool list for an agent, bound to ``project_path``."""
    root = project_path
    return [
        partial(repo.read_agents_md, root),
        partial(repo.read_file, root),
        partial(repo.list_projects, root),
        partial(repo.write_file, root),
        partial(run_shell_command, root),
        partial(repo.create_branch, root),
        partial(repo.git_add, root),
        partial(repo.git_commit, root),
    ]


def run_shell_command(root: Path):
    return partial(run_shell, root)
