"""Tests for ai_news.sources: feed parsing, date handling, recency filter, dedup."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from ai_news.sources import (
    dedupe,
    filter_recent,
    fetch_feed,
    normalize_url,
    parse_feed,
    parse_feed_date,
)

NOW = datetime(2026, 8, 30, 7, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------- parsing


def test_parse_rss_items(rss_sample):
    articles = parse_feed(rss_sample, source="Test Feed")
    assert [a.title for a in articles] == [
        "Open-source model tops benchmark",
        "Funding round for inference startup",
        "Old post",
        "Undated post",
    ]
    assert all(a.source == "Test Feed" for a in articles)


def test_parse_rss_guid_and_url(rss_sample):
    a = parse_feed(rss_sample, source="Test Feed")[0]
    assert a.url.startswith("https://example.com/2026/08/29/open-source-model")
    assert a.guid == a.url


def test_parse_rss_strips_html_and_normalizes_whitespace(rss_sample):
    a = parse_feed(rss_sample, source="Test Feed")[0]
    assert a.summary == "Team released an open-source model. It tops the benchmark. The weights are on the hub."


def test_parse_rss_pubdate(rss_sample):
    a = parse_feed(rss_sample, source="Test Feed")[0]
    assert a.published == datetime(2026, 8, 29, 14, 0, tzinfo=timezone.utc)
    assert not a.date_unknown


def test_parse_rss_undated_item(rss_sample):
    a = parse_feed(rss_sample, source="Test Feed")[3]
    assert a.published is None
    assert a.date_unknown


def test_parse_atom_entry(atom_sample):
    articles = parse_feed(atom_sample, source="Atom Feed")
    assert len(articles) == 1
    a = articles[0]
    assert a.title == "Research paper on reasoning"
    assert a.url == "https://atom.example.com/paper"
    # Atom: prefer <published> over <updated>, guid falls back to <id>
    assert a.published == datetime(2026, 8, 29, 8, 0, tzinfo=timezone.utc)
    assert a.guid == "urn:atom:1"


def test_parse_atom_without_published_uses_updated(atom_sample):
    no_published = atom_sample.replace(
        b"<published>2026-08-29T08:00:00Z</published>", b""
    )
    a = parse_feed(no_published, source="Atom Feed")[0]
    assert a.published == datetime(2026, 8, 30, 1, 0, tzinfo=timezone.utc)


def test_parse_unknown_format_raises(rss_sample):
    with pytest.raises(ValueError):
        parse_feed(b"<html><body>not a feed</body></html>", source="X")


def test_parse_empty_channel(rss_sample):
    empty = b'<rss version="2.0"><channel><title>Empty</title></channel></rss>'
    assert parse_feed(empty, source="X") == []


# ---------------------------------------------------------------- dates


def test_parse_feed_date_rfc822():
    assert parse_feed_date("Fri, 29 Aug 2026 14:00:00 +0000") == datetime(
        2026, 8, 29, 14, 0, tzinfo=timezone.utc
    )


def test_parse_feed_date_iso_z():
    assert parse_feed_date("2026-08-29T08:00:00Z") == datetime(
        2026, 8, 29, 8, 0, tzinfo=timezone.utc
    )


def test_parse_feed_date_naive_assumed_utc():
    assert parse_feed_date("2026-08-29T08:00:00") == datetime(
        2026, 8, 29, 8, 0, tzinfo=timezone.utc
    )


def test_parse_feed_date_offset_converted():
    d = parse_feed_date("2026-08-29T23:30:00+05:30")
    assert d == datetime(2026, 8, 29, 18, 0, tzinfo=timezone.utc)


def test_parse_feed_date_garbage_returns_none():
    assert parse_feed_date("not a date") is None
    assert parse_feed_date(None) is None


# ---------------------------------------------------------------- recency


def _articles_around_now():
    from ai_news.models import Article

    def mk(url, hours_ago, **kw):
        pub = NOW - timedelta(hours=hours_ago)
        base = dict(source="S", title=url, summary="", published=pub)
        base.update(kw)
        return Article(url=url, **base)

    return [
        mk("https://x/a", hours_ago=1),      # in window
        mk("https://x/b", hours_ago=25),     # in window (26h)
        mk("https://x/c", hours_ago=27),     # out of window
        mk("https://x/d", hours_ago=100),    # out of window
    ]


def test_filter_recent_keeps_window_and_drops_old():
    kept = filter_recent(_articles_around_now(), since=NOW - timedelta(hours=26))
    assert [a.url for a in kept] == ["https://x/a", "https://x/b"]


def test_filter_recent_undated_included_by_default():
    from ai_news.models import Article

    arts = _articles_around_now() + [Article(source="S", title="u", url="https://x/u", summary="")]
    kept = filter_recent(arts, since=NOW - timedelta(hours=26))
    assert "https://x/u" in [a.url for a in kept]


def test_filter_recent_undated_excluded_when_disabled():
    from ai_news.models import Article

    arts = _articles_around_now() + [Article(source="S", title="u", url="https://x/u", summary="")]
    kept = filter_recent(arts, since=NOW - timedelta(hours=26), include_undated=False)
    assert "https://x/u" not in [a.url for a in kept]


# ---------------------------------------------------------------- dedup


def test_normalize_url():
    assert normalize_url("HTTPS://X.COM/a?utm_source=rss#frag") == "https://x.com/a"
    assert normalize_url("https://x.com/a?b=2&utm_campaign=1") == "https://x.com/a?b=2"


def test_dedupe_keeps_newest_and_collapses_tracking_variants():
    from ai_news.models import Article

    old = Article(source="A", title="t1", url="https://x.com/a?utm_source=rss",
                  published=datetime(2026, 8, 28, tzinfo=timezone.utc), summary="")
    new = Article(source="B", title="t1 (updated)", url="https://x.com/a?utm_source=twitter",
                  published=datetime(2026, 8, 29, tzinfo=timezone.utc), summary="")
    other = Article(source="C", title="t2", url="https://x.com/b", published=None, summary="")

    kept = dedupe([old, new, other])
    assert [a.url for a in kept] == ["https://x.com/a?utm_source=twitter", "https://x.com/b"]
    assert kept[0].source == "B"


# ---------------------------------------------------------------- fetch


def test_fetch_feed_uses_injected_transport(fake_transport):
    articles = fetch_feed("https://ok.example.com/feed", source="T", transport=fake_transport)
    assert len(articles) == 4
    assert all(a.source == "T" for a in articles)


def test_fetch_feed_atom(fake_transport):
    articles = fetch_feed("https://atom.example.com/feed", source="A", transport=fake_transport)
    assert articles[0].title == "Research paper on reasoning"


def test_fetch_feed_network_error_raises():
    from ai_news.sources import FeedError

    def boom(url):
        raise ConnectionError("boom")

    with pytest.raises(FeedError):
        fetch_feed("https://down.example.com/feed", source="T", transport=boom)
