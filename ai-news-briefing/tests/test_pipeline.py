"""Tests for ai_news.pipeline: end-to-end run with injected fakes."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from ai_news.config import Settings
from ai_news.models import Article
from ai_news.pipeline import fetch_all, run_pipeline

NOW = datetime(2026, 8, 30, 7, 0, tzinfo=timezone.utc)

# RSS with one in-window, one out-of-window, one duplicate (tracking variant)
PIPELINE_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>F</title>
<item>
  <title>Model release</title>
  <link>https://n.example.com/release?utm_source=rss</link>
  <pubDate>Fri, 29 Aug 2026 20:00:00 +0000</pubDate>
  <description>Lab released a new model. It is open source.</description>
</item>
<item>
  <title>Model release (duplicate)</title>
  <link>https://n.example.com/release?utm_source=twitter</link>
  <pubDate>Fri, 29 Aug 2026 20:00:00 +0000</pubDate>
  <description>Lab released a new model. It is open source.</description>
</item>
<item>
  <title>Old story</title>
  <link>https://n.example.com/old</link>
  <pubDate>Thu, 28 Aug 2026 08:00:00 +0000</pubDate>
  <description>Stale.</description>
</item>
</channel></rss>
"""


def _settings(tmp_path) -> Settings:
    return Settings(
        feeds=[
            {"name": "Good", "url": "https://ok.example.com/feed"},
            {"name": "Bad", "url": "https://down.example.com/feed"},
        ],
        output_dir=tmp_path / "reports",
        state_file=tmp_path / "state" / "seen.json",
        window_hours=26,
        max_items=40,
    )


def _transport(url: str) -> bytes:
    if url == "https://ok.example.com/feed":
        return PIPELINE_RSS
    if url == "https://ok2.example.com/feed":
        return b'<rss version="2.0"><channel><title>Empty</title></channel></rss>'
    raise TimeoutError(f"no route to {url}")


class _FakeSummarizer:
    mode = "heuristic"

    def summarize(self, articles):
        from ai_news.models import Briefing, BriefingItem, BriefingSection

        items = [BriefingItem(article=a, bullets=[a.title.upper()]) for a in articles]
        return Briefing(
            sections=[BriefingSection(title="Other", items=items)],
            mode=self.mode,
            generated_at=NOW,
        )


def test_fetch_all_records_per_source_status(tmp_path):
    s = _settings(tmp_path)
    articles, status = fetch_all(s, transport=_transport)
    by_name = {x.name: x for x in status}
    assert by_name["Good"].ok and by_name["Good"].count == 3
    assert not by_name["Bad"].ok
    assert "no route" in by_name["Bad"].error
    assert len(articles) == 3


def test_run_pipeline_writes_dated_report_and_dedupes(tmp_path):
    s = _settings(tmp_path)
    path = run_pipeline(s, now=NOW, transport=_transport, summarizer=_FakeSummarizer())

    assert path.name == "2026-08-30.md"
    assert path.parent == tmp_path / "reports"
    content = path.read_text()
    assert "# AI News Briefing — 2026-08-30" in content
    # the tracking-param duplicate must collapse to one briefing entry
    assert content.count("[Model release") == 1
    # the out-of-window story must not appear
    assert "Old story" not in content
    # failing source reported in the footer
    assert "error: no route" in content


def test_run_pipeline_marks_seen_and_skips_next_morning(tmp_path):
    s = _settings(tmp_path)

    first = run_pipeline(s, now=NOW, transport=_transport, summarizer=_FakeSummarizer())
    assert "MODEL RELEASE" in first.read_text()  # upper-cased by the fake

    # next morning: same feed content, nothing new
    second = run_pipeline(
        s, now=NOW + timedelta(hours=12), transport=_transport, summarizer=_FakeSummarizer()
    )
    content = second.read_text()
    assert "No new AI news" in content
    assert "MODEL RELEASE" not in content


def test_run_pipeline_marks_all_window_items_even_over_cap(tmp_path):
    """Items dropped by max_items are still marked seen so they cannot reappear."""
    s = _settings(tmp_path)
    s.feeds = [{"name": "Good", "url": "https://ok.example.com/feed"}]
    s.max_items = 1  # only one of the two deduped items will be reported
    # two distinct in-window stories needed: reuse feed content via two feed entries?
    # simpler: raise cap-handling by feeding 2 distinct stories
    s.max_items = 1

    rss = PIPELINE_RSS.replace(
        b"<title>Old story</title>", b"<title>Second model launch</title>"
    ).replace(
        b"<pubDate>Thu, 28 Aug 2026 08:00:00 +0000</pubDate>",
        b"<pubDate>Fri, 29 Aug 2026 18:00:00 +0000</pubDate>",
    ).replace(b"https://n.example.com/old", b"https://n.example.com/second")
    s.feeds = [
        {"name": "Good", "url": "https://ok.example.com/feed"},
        {"name": "Good2", "url": "https://ok2.example.com/feed"},
    ]
    ok2 = rss  # second feed also serves the "second" story variant
    transport = lambda url: (PIPELINE_RSS if url.endswith("ok.example.com/feed") else ok2)  # noqa: E731

    first = run_pipeline(s, now=NOW, transport=transport, summarizer=_FakeSummarizer())
    second = run_pipeline(
        s, now=NOW + timedelta(hours=12), transport=transport, summarizer=_FakeSummarizer()
    )
    # the item that was dropped by the cap must not resurface
    assert "SECOND MODEL LAUNCH" not in second.read_text()


def test_run_pipeline_llm_mode_end_to_end(tmp_path, fake_llm):
    from ai_news.agent import SummarizeAgent

    s = _settings(tmp_path)
    s.feeds = [{"name": "Good", "url": "https://ok.example.com/feed"}]
    agent = SummarizeAgent(llm=fake_llm)
    path = run_pipeline(s, now=NOW, transport=_transport, summarizer=agent)
    content = path.read_text()
    assert "heuristic" not in content  # metadata line says llm
    assert "llm" in content
    # ref 1 in the canned LLM JSON points at the first (oldest) article...
    # the agent maps refs to the list it was given; verify a link is grounded
    assert "https://n.example.com/release" in content


def test_run_pipeline_empty_feeds_still_writes_report(tmp_path):
    s = _settings(tmp_path)
    s.feeds = [{"name": "Empty", "url": "https://ok2.example.com/feed"}]
    path = run_pipeline(s, now=NOW, transport=_transport, summarizer=_FakeSummarizer())
    assert "No new AI news" in path.read_text()


def test_run_pipeline_all_feeds_down_still_writes_report(tmp_path):
    s = _settings(tmp_path)
    s.feeds = [{"name": "Bad", "url": "https://down.example.com/feed"}]
    path = run_pipeline(s, now=NOW, transport=_transport, summarizer=_FakeSummarizer())
    content = path.read_text()
    assert "No new AI news" in content
    assert "error: no route" in content
