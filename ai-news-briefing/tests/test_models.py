"""Tests for ai_news.models: Article construction and normalized dedup keys."""
from __future__ import annotations

from datetime import datetime, timezone

from ai_news.models import Article


def _article(url: str, **kw) -> Article:
    base = dict(source="S", title="T", summary="", published=None)
    base.update(kw)
    return Article(url=url, **base)


def test_guid_defaults_to_url():
    a = _article("https://x.example.com/a")
    assert a.guid == "https://x.example.com/a"


def test_guid_explicit_kept():
    a = _article("https://x.example.com/a", guid="urn:custom:1")
    assert a.guid == "urn:custom:1"


def test_normalize_url_strips_tracking_params_and_fragment():
    a = _article("https://Example.com/a?utm_source=rss&id=1#frag")
    assert a.key == "https://example.com/a?id=1"


def test_normalize_url_lowercases_host_keeps_other_params():
    a = _article("HTTPS://EXAMPLE.COM/a?b=2")
    assert a.key == "https://example.com/a?b=2"


def test_same_story_different_tracking_params_share_key():
    a = _article("https://x.example.com/a?utm_source=twitter")
    b = _article("https://x.example.com/a?utm_source=rss")
    assert a.key == b.key


def test_date_unknown_defaults_from_published():
    a = _article("https://x.example.com/a", published=datetime(2026, 8, 29, tzinfo=timezone.utc))
    b = _article("https://x.example.com/b")
    assert not a.date_unknown
    assert b.date_unknown
