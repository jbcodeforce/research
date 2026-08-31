"""Markdown rendering and atomic report writing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

from .models import Article, Briefing, BriefingItem, BriefingSection

_TMP_SUFFIX = ".tmp-{}"


@dataclass
class SourceStatus:
    """The outcome of fetching a single feed during a run."""

    name: str
    ok: bool
    count: int = 0
    error: str | None = None

    @property
    def status_text(self) -> str:
        return "ok" if self.ok else f"error: {self.error}"


def _fmt_article_date(article: Article) -> str:
    if article.published is not None:
        return article.published.strftime("%Y-%m-%d")
    return "date unknown"


def render_markdown(briefing: Briefing, day: date, statuses: list[SourceStatus] | None = None) -> str:
    """Render a briefing into markdown, including an optional feed-status footer."""
    lines: list[str] = []
    total = sum(len(s.items) for s in briefing.sections)

    lines.append(f"# AI News Briefing — {day.isoformat()}")
    lines.append("")
    label = f"{total} item{'s' if total != 1 else ''}"
    generated = briefing.generated_at.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"**Summary** — {briefing.mode} mode · {label} · generated {generated} UTC")

    for section in briefing.sections:
        lines.append("")
        lines.append(f"## {section.title}")
        for item in section.items:
            article = item.article
            lines.append(f"- [{article.title}]({article.url}) — {article.source}, {_fmt_article_date(article)}")
            for bullet in item.bullets:
                lines.append(f"  - {bullet}")
    if not briefing.sections:
        lines.append("")
        lines.append("No new AI news for this run.")
        lines.append("")

    if statuses:
        ok_count = sum(1 for s in statuses if s.ok)
        lines.append("")
        lines.append(f"## Feed status · feeds: {len(statuses)} · ok: {ok_count} · error: {len(statuses) - ok_count}")
        lines.append("")
        lines.append("| Source | Items | Status |")
        lines.append("| --- | --- | --- |")
        for status in statuses:
            lines.append(f"| {status.name} | {status.count} | {status.status_text} |")
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _render_idempotent(briefing: Briefing, day: date, statuses: list[SourceStatus] | None) -> str:
    # The render pipeline is pure: identical inputs must yield identical output,
    # which keeps reports deterministic across runs.
    return render_markdown(briefing, day, statuses)


def write_report(path: Path | str, content: str) -> Path:
    """Write ``content`` to ``path`` atomically (tmp file + rename).

    Returns the target path. No partial file is ever left behind on success.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{_TMP_SUFFIX.format(id(path))}")
    tmp.write_text(content, encoding="utf-8")
    tmp.replace(path)
    return path
