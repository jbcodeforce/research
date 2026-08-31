"""Tests for ai_news.report: markdown rendering and atomic report writing."""
from __future__ import annotations

from datetime import date, datetime, timezone

from ai_news.models import Article, Briefing, BriefingItem, BriefingSection
from ai_news.report import SourceStatus, render_markdown, write_report


def _article(title, url, source="VentureBeat AI", when=None):
    return Article(
        source=source,
        title=title,
        url=url,
        summary="",
        published=when,
    )


def _briefing(mode="llm"):
    day = datetime(2026, 8, 29, 15, 0, tzinfo=timezone.utc)
    undated = _article("Undated item", "https://a/undated", source="Ars Technica AI")
    dated = _article("Model release", "https://a/release", when=day)
    section = BriefingSection(
        title="Models & Releases",
        items=[
            BriefingItem(article=dated, bullets=["Point one", "Point two"]),
            BriefingItem(article=undated, bullets=["No date on this one"]),
        ],
    )
    return Briefing(sections=[section], mode=mode, generated_at=datetime(2026, 8, 30, 7, 5, tzinfo=timezone.utc))


def test_title_contains_date():
    md = render_markdown(_briefing(), date(2026, 8, 30), [])
    assert md.splitlines()[0] == "# AI News Briefing — 2026-08-30"


def test_metadata_line_shows_mode_and_count():
    md = render_markdown(_briefing(mode="heuristic"), date(2026, 8, 30), [])
    assert "2 items" in md
    assert "heuristic" in md
    assert "2026-08-30" in md  # generation timestamp in UTC


def test_item_renders_link_source_date_and_bullets():
    md = render_markdown(_briefing(), date(2026, 8, 30), [])
    assert "- [Model release](https://a/release) — VentureBeat AI, 2026-08-29" in md
    assert "  - Point one" in md
    assert "  - Point two" in md


def test_undated_item_marks_date_unknown():
    md = render_markdown(_briefing(), date(2026, 8, 30), [])
    assert "date unknown" in md


def test_item_without_bullets_renders_title_only():
    a = _article("Bare", "https://a/bare")
    b = Briefing(
        sections=[BriefingSection(title="Other", items=[BriefingItem(article=a, bullets=[])])],
        mode="heuristic",
        generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc),
    )
    md = render_markdown(b, date(2026, 8, 30), [])
    assert "- [Bare](https://a/bare)" in md
    assert "  -" not in md.split("## Other", 1)[1]


def test_no_news_renders_placeholder():
    empty = Briefing(sections=[], mode="llm", generated_at=datetime(2026, 8, 30, tzinfo=timezone.utc))
    md = render_markdown(empty, date(2026, 8, 30), [])
    assert "No new AI news" in md


def test_source_status_table():
    status = [
        SourceStatus(name="VentureBeat AI", ok=True, count=5, error=None),
        SourceStatus(name="OpenAI News", ok=False, count=0, error="timeout"),
    ]
    md = render_markdown(_briefing(), date(2026, 8, 30), status)
    assert "| VentureBeat AI | 5 | ok |" in md
    assert "| OpenAI News | 0 | error: timeout |" in md
    assert "feeds: 2" in md
    assert "ok: 1" in md


def test_render_is_idempotent():
    a = _briefing()
    assert render_markdown(a, date(2026, 8, 30), []) == render_markdown(a, date(2026, 8, 30), [])


def test_write_report_creates_file_with_content(tmp_path):
    path = write_report(tmp_path / "2026-08-30.md", "# hello")
    assert path == tmp_path / "2026-08-30.md"
    assert path.read_text() == "# hello"


def test_write_report_creates_parent_dirs(tmp_path):
    path = write_report(tmp_path / "nested" / "reports" / "x.md", "y")
    assert path.read_text() == "y"


def test_write_report_is_atomic_no_partial_file(tmp_path):
    # after a successful write there must be no leftover temp files
    write_report(tmp_path / "r.md", "content")
    assert [p.name for p in tmp_path.iterdir()] == ["r.md"]
