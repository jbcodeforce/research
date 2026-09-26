"""Deterministic filesystem and git helpers.

All file helpers are rooted at ``root`` (the project folder) so they are
independent of the current working directory and trivially unit testable. Git
helpers operate on the enclosing git repository (found by walking up the tree).
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List, Optional, Union

from research_harness.state import slugify
from research_harness.tools.shell import run_shell


def resolve(path: Union[str, Path], root: Path) -> Path:
    """Resolve a relative path against ``root`` without creating it."""
    p = Path(path)
    if p.is_absolute():
        return Path(p)
    return (root / p).resolve()


def write_file(root: Path, path: Union[str, Path], content: str) -> Path:
    """Write ``content`` to ``path`` (relative to ``root``), creating parents."""
    target = resolve(path, root)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return target


def read_file(root: Path, path: Union[str, Path], default: str = "") -> str:
    """Read a text file relative to ``root``; returns ``default`` if missing."""
    p = resolve(path, root)
    if not p.is_file():
        return default
    return p.read_text(encoding="utf-8")


def exists(path: Union[str, Path], root: Path) -> bool:
    """Return whether ``path`` exists relative to ``root``."""
    return resolve(path, root).is_file()


def ensure_folder(dir_path: Union[str, Path], root: Path) -> Path:
    """Create a directory (relative to ``root``) if it does not exist."""
    target = resolve(dir_path, root)
    target.mkdir(parents=True, exist_ok=True)
    return target


def list_projects(root: Path) -> List[str]:
    """Return names of sub-directories (the independent research projects)."""
    if not root.is_dir():
        return []
    return sorted(
        p.name
        for p in root.iterdir()
        if p.is_dir() and not p.name.startswith(".") and p.name not in {"__pycache__"}
    )


def _git_root(root: Path) -> Optional[Path]:
    """Find the enclosing git repository by walking up the directory tree."""
    cur = root.resolve()
    while True:
        if (cur / ".git").exists():
            return cur
        parent = cur.parent
        if parent == cur:
            return None
        cur = parent


def current_branch(root: Path) -> Optional[str]:
    """Return the checked-out branch name (or ``None``/``untracked`` if unborn)."""
    try:
        return run_shell("git rev-parse --abbrev-ref HEAD", cwd=root).stdout.strip()
    except RuntimeError:
        res = run_shell("git status --porcelain --branch", cwd=root, check=False)
        if res.returncode == 0 and res.stdout.startswith("* "):
            return res.stdout[2:].split()[0]
        return "untracked"


def git_add(root: Path, paths: Iterable[Union[str, Path]] = ()) -> None:
    """``git add`` the given paths relative to ``root``."""
    from research_harness.tools.shell import run_shell

    run_shell("git add --", cwd=root, args=[str(p) for p in paths])


def git_commit(root: Path, message: str, paths: Iterable[Union[str, Path]] = ()) -> Optional[str]:
    """Create a commit and return its SHA."""
    import shlex

    from research_harness.tools.shell import run_shell

    run_shell("git config user.email 'research@localhost'")
    run_shell("git config user.name 'Research Harness'")
    # shell-quoted so the message (which may contain ':' or spaces) is one token
    run_shell("git commit -m", cwd=root, args=[shlex.quote(message)], check=False)
    out = run_shell("git rev-parse HEAD", cwd=root).stdout.strip()
    return out or None


def create_branch(root: Path, name: str) -> bool:
    """Create (and checkout) ``name`` if it does not already exist."""
    if current_branch(root) == name:
        return True
    ok = run_shell("git checkout -b", cwd=root, args=[name], check=False).success
    return ok


def read_agents_md(root: Path, default: str = "") -> str:
    """Read the root ``AGENTS.md``; fall back to ``default`` if absent."""
    git_root = _git_root(root)
    if git_root is None:
        return default
    return read_file(git_root, "AGENTS.md", default=default)
