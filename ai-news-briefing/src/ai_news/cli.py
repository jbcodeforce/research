"""Command-line interface: ``ai-news run`` | ``list-sources`` | ``test-llm``."""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

from .agent import LLMClient, LLMError
from .config import load_dotenv_file, load_settings, project_root
from .pipeline import run_pipeline


def _collect_env_overrides() -> dict[str, str]:
    """Read AI_NEWS_* variables from the process environment as overrides."""
    return {k: v for k, v in os.environ.items() if k.startswith("AI_NEWS_")}


def _load_settings(args) -> object:
    overrides = _collect_env_overrides()
    overrides.update(load_dotenv_file(project_root() / ".env"))
    config_path = getattr(args, "config", None)
    if config_path is None:
        config_path = os.environ.get("AI_NEWS_CONFIG")
    return load_settings(config_path, env=overrides)


def _disable_llm(settings) -> None:
    settings.llm_base_url = None
    settings.llm_api_key = None
    settings.llm_model = None


def _parse_date_or_midnight(value: str) -> datetime:
    """A --date value anchors a backfill to UTC midnight of that day."""
    try:
        return datetime.fromisoformat(value + "T00:00:00")
    except ValueError:
        return datetime.fromisoformat(value).replace(tzinfo=None, hour=0, minute=0, second=0)


def cmd_run(args) -> int:
    settings = _load_settings(args)

    if args.no_llm:
        _disable_llm(settings)
    if args.window_hours is not None:
        settings.window_hours = args.window_hours
    if args.max_items is not None:
        settings.max_items = args.max_items
    if args.output_dir:
        settings.output_dir = Path(args.output_dir)
    if args.state_file:
        settings.state_file = Path(args.state_file)

    now = _parse_date_or_midnight(args.date) if args.date else None
    report_path = run_pipeline(settings, now=now)
    print(str(report_path))
    return 0


def cmd_list_sources(args) -> int:
    settings = _load_settings(args)
    if not settings.feeds:
        print("no feeds configured")
        return 0
    for feed in settings.feeds:
        print(f"{feed.name}: {feed.url}")
    return 0


def build_llm_client(settings) -> LLMClient:
    if not settings.has_llm:
        raise LLMError("no llm configured")
    return LLMClient(
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        max_tokens=settings.llm_max_tokens,
    )


def cmd_test_llm(args) -> int:
    settings = _load_settings(args)
    if not settings.has_llm:
        print("not configured: set AI_NEWS_LLM_BASE_URL, AI_NEWS_LLM_API_KEY and AI_NEWS_LLM_MODEL")
        return 1
    client = build_llm_client(settings)
    try:
        result = client.chat("test the LLM connection", "ping")
    except LLMError as exc:
        print(f"llm error: {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001 - surface any transport failure cleanly
        print(f"error: {exc}")
        return 1
    print(result)
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-news", description="Morning AI news briefing agent.")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Fetch feeds and write a dated briefing report.")
    run.add_argument("--config", help="Path to a sources.json config file.")
    run.add_argument("--date", help="Backfill a specific date (UTC midnight).")
    run.add_argument("--no-llm", action="store_true", help="Force heuristic summarization.")
    run.add_argument("--window-hours", type=int, help="Override the recency window.")
    run.add_argument("--max-items", type=int, help="Override the number of briefed items.")
    run.add_argument("--output-dir", help="Override the output directory.")
    run.add_argument("--state-file", help="Override the seen-store file.")
    run.set_defaults(func=cmd_run)

    list_sources = sub.add_parser("list-sources", help="List configured feeds.")
    list_sources.set_defaults(func=cmd_list_sources)

    test_llm = sub.add_parser("test-llm", help="Test the configured LLM connection.")
    test_llm.set_defaults(func=cmd_test_llm)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
