"""Tool callables exposed to the research agents.

agno wraps each tool and calls it with the arguments the agent passes. This
module binds the project root once and returns the full tool list for an agent.

The source functions in :mod:`research_harness.tools.repo` and
:mod:`research_harness.tools.shell` are plain callables. Here we produce a
proper agno ``Function`` for each one: ``root`` is pre-bound and stripped from
the JSON schema so the agent only sees the arguments it should control.
"""

from __future__ import annotations

import functools
import inspect
from pathlib import Path
from typing import Callable

from agno.tools.function import Function

from research_harness.tools import repo, run_shell


def _bind_root(func: Callable, root: Path) -> Function:
    """Return an agno ``Function`` with ``root`` pre-bound and removed from the schema.

    Wraps ``func`` so ``root`` is always supplied, rewrites ``__signature__``
    to drop that first parameter, then converts the result to a ``Function``
    via ``Function.from_callable`` so agno builds the correct JSON schema.
    """

    @functools.wraps(func)
    def bound(*args, **kwargs):
        return func(root, *args, **kwargs)

    # Drop the first parameter (root) so agno sees the agent-facing signature.
    sig = inspect.signature(func)
    params = list(sig.parameters.values())
    bound.__signature__ = sig.replace(parameters=params[1:])

    return Function.from_callable(bound)


def bind_tools(project_path: Path) -> list:
    """Return the full tool list for an agent, bound to ``project_path``."""
    root = project_path
    return [
        _bind_root(repo.read_agents_md, root),
        _bind_root(repo.read_file, root),
        _bind_root(repo.list_projects, root),
        _bind_root(repo.write_file, root),
        _bind_root(run_shell, root),
        _bind_root(repo.create_branch, root),
        _bind_root(repo.git_add, root),
        _bind_root(repo.git_commit, root),
    ]
