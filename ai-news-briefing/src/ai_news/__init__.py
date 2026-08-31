"""ai-news-briefing: agentic morning briefing of the latest AI news."""

from __future__ import annotations

from .config import (
    Feed,
    Settings,
    default_settings,
    load_dotenv_file,
    load_settings,
    project_root,
)
from .pipeline import run_pipeline
from .sources import dedupe, fetch_all, fetch_feed, filter_recent, parse_feed, SourceStatus

__all__ = [
    "Feed",
    "Settings",
    "default_settings",
    "load_dotenv_file",
    "load_settings",
    "project_root",
    "run_pipeline",
    "dedupe",
    "fetch_all",
    "fetch_feed",
    "filter_recent",
    "parse_feed",
    "SourceStatus",
]

__version__ = "0.1.0"
