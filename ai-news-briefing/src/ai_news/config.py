"""Configuration: settings objects, defaults, JSON config loading, .env handling."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@dataclass
class Feed:
    """A single RSS/Atom source referenced by name and URL."""

    name: str
    url: str


# Mapping of an ``AI_NEWS_*`` env var to a Settings attribute name.
_ENV_TO_ATTR = {}
for _k, _v in {
    "LLM_BASE_URL": "llm_base_url",
    "LLM_API_KEY": "llm_api_key",
    "LLM_MODEL": "llm_model",
    "LLM_TIMEOUT": "llm_timeout",
    "LLM_MAX_TOKENS": "llm_max_tokens",
    "OUTPUT_DIR": "output_dir",
    "STATE_FILE": "state_file",
    "WINDOW_HOURS": "window_hours",
    "MAX_ITEMS": "max_items",
}.items():
    _ENV_TO_ATTR["AI_NEWS_" + _k] = _v


def project_root() -> Path:
    """Return the repository root (the folder holding ``config/sources.json``).

    Resolved from the package location so it works regardless of the current
    working directory.
    """
    return PROJECT_ROOT


def load_dotenv_file(path: Path | str) -> dict[str, str]:
    """Parse a dotenv file into a dict without touching the real environment.

    Returns an empty dict when the file does not exist. This is intentionally
    side-effect free: the caller is responsible for merging the result into the
    process environment if desired.
    """
    path = Path(path)
    if not path.is_file():
        return {}
    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        result[key.strip()] = value.strip().removesuffix("\n")
    return result


def _load_config_or_defaults(config_path: Path | str | None) -> Feed:
    """Load feeds from JSON config, falling back to defaults on any problem.

    A missing file or unreadable/invalid JSON is not fatal: we return the
    bundled default sources so an unattended run still produces output.
    """
    if config_path and Path(config_path).is_file():
        try:
            data = json.loads(Path(config_path).read_text(encoding="utf-8"))
            feeds = data.get("feeds", [])
            if isinstance(feeds, list):
                return Feed(feeds)
        except (OSError, ValueError):
            pass
    return Feed.from_sources_json()


@dataclass
class Settings:
    """Runtime configuration for a briefing run.

    ``has_llm`` is true only when both a base URL *and* a model are set, which
    mirrors the requirement that an OpenAI-compatible endpoint needs both to be
    usable.
    """

    feeds: list[Feed] = field(default_factory=list)
    output_dir: Path = field(default_factory=lambda: PROJECT_ROOT / "reports")
    state_file: Path = field(default_factory=lambda: PROJECT_ROOT / "state" / "seen.json")
    window_hours: int = 26
    max_items: int = 40
    llm_base_url: str | None = None
    llm_api_key: str | None = None
    llm_model: str | None = None
    llm_timeout: int = 180
    llm_max_tokens: int = 4096

    @property
    def has_llm(self) -> bool:
        return bool(self.llm_base_url) and bool(self.llm_model)

    @classmethod
    def from_sources_json(cls) -> "Settings":
        """Build default settings from the bundled ``config/sources.json``."""
        feeds = []
        sources_path = PROJECT_ROOT / "config" / "sources.json"
        if sources_path.is_file():
            try:
                data = json.loads(sources_path.read_text(encoding="utf-8"))
                for entry in data.get("feeds", []):
                    feeds.append(Feed(name=entry["name"], url=entry["url"]))
            except (OSError, ValueError, KeyError, TypeError):
                pass
        return cls(feeds=feeds)

    @classmethod
    def _apply_env(cls, feeds: list[Feed], overrides: dict[str, str]) -> "Settings":
        """Copy default settings and override fields driven by env var names."""
        s = cls(feeds=feeds)
        for env_key, value in overrides.items():
            attr = _ENV_TO_ATTR.get(env_key)
            if attr is None:
                continue
            if hasattr(s, attr):
                setattr(s, attr, value)
        return s


def default_settings(
    output_dir: Path | str | None = None,
    state_file: Path | str | None = None,
) -> Settings:
    """Build default settings (bundled feeds) with optional output paths."""
    s = Settings.from_sources_json()
    if output_dir is not None:
        s.output_dir = Path(output_dir)
    if state_file is not None:
        s.state_file = Path(state_file)
    return s


def load_settings(
    config_path: Path | str | None = None,
    env: dict[str, str] | None = None,
) -> Settings:
    """Load settings from JSON config, applying environment overrides.

    ``env`` is an optional dict of environment overrides. When ``None`` we read
    the live process environment (expected to already include the project
    ``.env``) and honor any ``AI_NEWS_*`` variables present.
    """
    overrides = {k: v for k, v in os.environ.items() if k.startswith("AI_NEWS_")}
    if env:
        overrides.update(env)
    feeds = _load_config_or_defaults(config_path).feeds
    return Settings._apply_env(feeds, overrides)
