"""Feed fetching and stream shaping: parse feeds, filter by recency, dedupe.

The lower-level helpers (``parse_feed``, ``parse_feed_date``, ``normalize_url``)
are shared with :mod:`ai_news.models`; the higher-level ones here decide
recency, deduplication, and network access.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterable

from .models import Article
from ._feed_util import normalize_url, parse_feed_date

# Callable used to fetch raw feed bytes by URL; injectable so tests can stub it.
Transport = Callable[[str], bytes]

HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_ATTR_RE = re.compile(r"\[([a-zA-Z0-9_:-]+)\]\(([^)]+)\)")


@dataclass
class FeedError(Exception):
    """Raised when a feed cannot be retrieved or parsed."""


def parse_feed(data: bytes | str, source: str) -> list[Article]:
    """Parse an RSS 2.0 or Atom feed body into a list of articles.

    Raises ``ValueError`` for content that is neither RSS nor Atom, and returns
    an empty list for an RSS/Atom feed with no items.
    """
    root = ET.fromstring(data)
    tag = _localname(root.tag)
    if tag == "rss":
        return _parse_rss(root, source)
    if tag == "feed":
        return _parse_atom(root, source)
    raise ValueError(f"unrecognized feed format: <{root.tag}>")


def parse_feed_date(value) -> datetime | None:
    """Parse a common RSS/Atom date string to a UTC-aware datetime."""
    return parse_feed_date(value)


def _localname(tag: str) -> str:
    """Return the tag name without any XML namespace prefix."""
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _strip_html(text: str | None) -> str:
    if not text:
        return ""
    return HTML_TAG_RE.sub(" ", text).strip()


def _collapse_ws(text: str) -> str:
    return WS_RE.sub(" ", text).strip()


def _parse_rss(channel, source: str) -> list[Article]:
    articles: list[Article] = []
    for item in channel.findall("item"):
        title = _first(item, "title")
        link = _first(item, "link")
        guid = _first(item, "guid")
        pub = _parse_item_date(item)
        summary = _first(item, "description")
        if not link and guid:
            link = guid
        articles.append(
            Article(
                url=link or "",
                source=source,
                title=title or "",
                summary=_strip_html(_collapse_ws(summary)),
                published=pub,
                guid=guid,
            )
        )
    return articles


def _parse_atom(feed, source: str) -> list[Article]:
    articles: list[Article] = []
    # Atom default namespace.
    ns = "{http://www.w3.org/2005/Atom}"
    for entry in feed.findall(ns + "entry") or feed.findall("entry"):
        title = _first(entry, ns + "title") or _first(entry, "title")
        link = _first_link(entry, ns)
        guid = _first(entry, ns + "id") or _first(entry, "id")
        summary = _first(entry, ns + "summary") or _first(entry, "content")
        summary = _strip_html(_collapse_ws(summary))
        # Atom: prefer <published>, fall back to <updated>.
        pub = _parse_atom_date(entry, ns)
        articles.append(
            Article(
                url=link or "",
                source=source,
                title=title or "",
                summary=summary,
                published=pub,
                guid=guid,
            )
        )
    return articles


def _first(parent, *tags) -> str | None:
    """Return the first non-empty text child matching any of ``tags``."""
    for tag in tags:
        el = parent.find(tag)
        if el is not None and el.text:
            return el.text.strip()
    return None


def _first_link(entry_or_item, ns) -> str | None:
    """Return the link text of the first element with the given tag attribute."""
    for el in entry_or_item:
        if _localname(el.tag) == "link":
            if el.attrib.get("rel") == "alternate":
                return el.attrib.get("href")
            return el.attrib.get("href")
    return None


def _parse_item_date(item) -> datetime | None:
    """Parse a date from an RSS item, trying pubDate, dc:date, content:encoded."""
    pub = _first(item, "pubDate")
    if pub:
        return parse_feed_date(pub)
    dc_date = _first(item, "{http://purl.org/dc/elements/1.1/}date")
    if dc_date:
        return parse_feed_date(dc_date)
    for attr in ("content:encoded", "content"):
        ns = "{http://purl.org/rss/1.0/modules/content/}"
        encoded = _first(item, ns + "encoded")
        if encoded:
            encoded = _ATTR_RE.search(encoded)
            if encoded:
                return parse_feed_date(encoded.group(2))
    return None


def _parse_atom_date(entry, ns) -> datetime | None:
    pub = _first(entry, ns + "published")
    if pub:
        return parse_feed_date(pub)
    upd = _first(entry, ns + "updated")
    if upd:
        return parse_feed_date(upd)
    return None


def filter_recent(
    articles: Iterable[Article],
    since: datetime,
    include_undated: bool = True,
) -> list[Article]:
    """Keep articles published at or after ``since``.

    Undated items are included when ``include_undated`` is true (the default)
    since most feeds are fresh; callers can opt out to drop them.
    """
    return [a for a in articles if a.published is None or a.published >= since]


def dedupe(articles: Iterable[Article]) -> list[Article]:
    """Collapse articles that share a normalized URL key.

    Keeps the newest instance per key (by publication date), which is what we
    want when a story reappears across feeds or with different tracking params.
    """
    kept: dict[str, Article] = {}
    for a in articles:
        current = kept.get(a.key)
        if current is None:
            kept[a.key] = a
        elif a.published is not None and (current.published is None or a.published > current.published):
            kept[a.key] = a
    return list(kept.values())


def fetch_feed(url: str, source: str, transport: Transport) -> list[Article]:
    """Fetch a feed via ``transport`` and parse it into articles.

    Any transport failure (network error, timeout, bad response) is wrapped in
    :class:`FeedError` so callers can record per-source status.
    """
    try:
        data = transport(url)
    except Exception as exc:  # noqa: BLE001 - a feed is one source; never abort the run
        raise FeedError(f"failed to fetch {source}: {exc}") from exc
    try:
        return parse_feed(data, source=source)
    except (ET.ParseError, ValueError) as exc:
        raise FeedError(f"failed to parse {source}: {exc}") from exc


def fetch_all(settings, transport: Transport) -> tuple[list[Article], list]:
    """Fetch and parse every configured feed, recording per-source status.

    Articles from all successful feeds are concatenated (dedup happens later in
    the pipeline). Failing feeds do not abort the run.
    """
    from .report import SourceStatus

    articles: list[Article] = []
    status: list[SourceStatus] = []
    for feed in settings.feeds:
        try:
            parsed = fetch_feed(feed.url, source=feed.name, transport=transport)
            articles.extend(parsed)
            status.append(SourceStatus(name=feed.name, ok=True, count=len(parsed), error=None))
        except FeedError as exc:
            status.append(SourceStatus(name=feed.name, ok=False, count=0, error=str(exc)))
    return articles, status
