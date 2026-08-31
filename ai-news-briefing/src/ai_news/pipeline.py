"""End-to-end pipeline: fetch feeds, keep only new in-window items, brief them."""

from __future__ import annotations

import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path

from .agent import build_summarizer
from .models import Article, Briefing
from .report import render_markdown
from .sources import dedupe, fetch_all, filter_recent, SourceStatus
from .state import SeenStore


def _sort_key(article: Article):
    """Newest-first; undated items sort last so dated news leads the brief."""
    if article.published is not None:
        return (0, article.published)
    return (1, datetime.min)


def _new_items(articles: list[Article], store: SeenStore) -> list[Article]:
    """Return in-window articles not briefed since the last run."""
    return [a for a in articles if not store.is_seen(a.key)]


def _empty_briefing(mode: str, now: datetime) -> Briefing:
    return Briefing(sections=[], mode=mode, generated_at=now)


def run_pipeline(
    settings,
    now: datetime | None = None,
    transport=None,
    summarizer=None,
) -> Path:
    """Run a full briefing and write the dated markdown report.

    Steps: fetch feeds -> keep in-window items -> drop already-seen -> summarize
    the *new* items (capped by max_items) -> mark every in-window item seen so
    the next morning's run only surfaces genuinely new stories.
    """
    now = now or datetime.now(timezone.utc)
    transport = transport or (lambda url: requests.get(url).content)
    summarizer = summarizer or build_summarizer(settings)

    all_articles, statuses = fetch_all(settings, transport)
    window_cutoff = now - timedelta(hours=settings.window_hours)
    deduped = dedupe(filter_recent(all_articles, since=window_cutoff))

    store = SeenStore(settings.state_file)
    store.load()
    # Mark every in-window item seen first, so the max_items cap never lets a
    # dropped-but-fresh story reappear on a later run.
    store.mark([a.key for a in deduped], when=now)
    new_items = _new_items(deduped, store)
    new_items.sort(key=_sort_key)

    if not new_items:
        md = render_markdown(_empty_briefing(settings.mode, now), now.date(), statuses or None)
    else:
        md = render_markdown(summarizer.summarize(new_items[: settings.max_items], now=now), now.date(), statuses or None)

    report_path = settings.output_dir / f"{now.strftime('%Y-%m-%d')}.md"
    store.save()
    return write_report(report_path, md)


def write_report(path: Path | str, content: str) -> Path:
    """Atomically write the report, creating parent directories."""
    from .report import write_report as _write

    return _write(path, content)
