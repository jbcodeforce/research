"""Domain objects: the article model and the structured briefing output."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from ._feed_util import normalize_url


@dataclass
class Article:
    """A single news item scraped from a feed.

    ``key`` is the normalized identifier used by the dedup/seen layers; it is
    derived from the (guid if present else) URL so the same story seen through
    tracking-parameter variants collapses to one record.
    """

    url: str
    source: str = ""
    title: str = ""
    summary: str = ""
    published: datetime | None = None
    guid: str | None = None

    def __post_init__(self) -> None:
        if self.guid is None or not self.guid:
            self.guid = self.url
        self.key = normalize_url(self.guid or self.url)

    @property
    def date_unknown(self) -> bool:
        """True when the item carries no parseable publication date."""
        return self.published is None


@dataclass
class BriefingItem:
    """One article referenced by a section, with the model's bullet points."""

    article: Article
    bullets: list[str] = field(default_factory=list)


@dataclass
class BriefingSection:
    """A thematic group of briefing items."""

    title: str
    items: list[BriefingItem] = field(default_factory=list)


@dataclass
class Briefing:
    """The full rendered-in-memory result of a summarization pass.

    ``mode`` records *how* it was produced ("llm" or "heuristic"); the report
    footer exposes it so operators can tell fallback runs apart.
    """

    sections: list[BriefingSection] = field(default_factory=list)
    mode: str = "heuristic"
    generated_at: datetime = field(default_factory=datetime.now)
