"""Shared fixtures: sample feeds, fake LLM transport, temp paths."""
from __future__ import annotations

import json

import pytest

RSS_SAMPLE = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"
     xmlns:dc="http://purl.org/dc/elements/1.1/"
     xmlns:content="http://purl.org/rss/1.0/modules/content/">
<channel>
  <title>Test Feed</title>
  <link>https://example.com</link>
  <item>
    <title>Open-source model tops benchmark</title>
    <link>https://example.com/2026/08/29/open-source-model?utm_source=rss&amp;utm_medium=feed</link>
    <guid>https://example.com/2026/08/29/open-source-model?utm_source=rss&amp;utm_medium=feed</guid>
    <pubDate>Fri, 29 Aug 2026 14:00:00 +0000</pubDate>
    <description><![CDATA[<p>Team released an open-source model. It tops the benchmark. The weights are on the hub.</p>]]></description>
  </item>
  <item>
    <title>Funding round for inference startup</title>
    <link>https://example.com/2026/08/29/funding</link>
    <pubDate>Fri, 29 Aug 2026 09:00:00 +0000</pubDate>
    <description>Startup raised a billion dollars to scale inference.</description>
  </item>
  <item>
    <title>Old post</title>
    <link>https://example.com/2026/08/01/old</link>
    <pubDate>Wed, 01 Aug 2026 09:00:00 +0000</pubDate>
    <description>Something old that should be filtered out.</description>
  </item>
  <item>
    <title>Undated post</title>
    <link>https://example.com/undated</link>
    <description>No date here.</description>
  </item>
</channel>
</rss>
"""

ATOM_SAMPLE = b"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <entry>
    <title>Research paper on reasoning</title>
    <link rel="alternate" href="https://atom.example.com/paper"/>
    <id>urn:atom:1</id>
    <published>2026-08-29T08:00:00Z</published>
    <updated>2026-08-30T01:00:00Z</updated>
    <summary>New paper on reasoning. It beats prior SOTA.</summary>
  </entry>
</feed>
"""

# LLM canned answer referencing article #1 only (2 bullets).
LLM_VALID_JSON = json.dumps(
    {
        "sections": [
            {
                "title": "Models &amp; Releases",
                "items": [
                    {
                        "ref": 1,
                        "bullets": [
                            "Released an open-source model",
                            "Tops the benchmark",
                        ],
                    }
                ],
            }
        ]
    }
)


class FakeLLM:
    """Callable with the same shape as the real LLMClient (for injection)."""

    def __init__(self, content: str | None = None, error: Exception | None = None):
        self._content = content if content is not None else LLM_VALID_JSON
        self._error = error
        self.calls: list[dict] = []

    def chat(self, system: str, user: str) -> str:
        self.calls.append({"system": system, "user": user})
        if self._error is not None:
            raise self._error
        return self._content


@pytest.fixture
def rss_sample() -> bytes:
    return RSS_SAMPLE


@pytest.fixture
def atom_sample() -> bytes:
    return ATOM_SAMPLE


@pytest.fixture
def fake_llm() -> FakeLLM:
    return FakeLLM()


@pytest.fixture
def fake_transport():
    """Fake requests-like transport for feed fetching: url -> bytes."""

    def _transport(url: str) -> bytes:
        if url == "https://ok.example.com/feed":
            return RSS_SAMPLE
        if url == "https://atom.example.com/feed":
            return ATOM_SAMPLE
        raise TimeoutError(f"no route to {url}")

    return _transport
