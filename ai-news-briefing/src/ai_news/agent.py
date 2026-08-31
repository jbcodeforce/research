"""Summarization: a deterministic heuristic fallback plus an LLM-backed agent.

Design intent (see notes.md): the LLM is only used for categorization and bullet
writing, and it must return *structured JSON that references real article ids*.
Titles, URLs, dates and sources always come from the feeds, so an unattended
cron run can never invent links. When the endpoint is down or misbehaves, the
pipeline transparently falls back to the heuristic summarizer.

The heuristic path is pure and offline; the LLM path is wrapped so any failure
(times out, returns bad JSON, HTTP error) collapses back to heuristic.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone

from .models import Article, Briefing, BriefingItem, BriefingSection
from .report import SourceStatus

# Canonical section order drives both classification buckets and output order.
# "Other" is intentionally excluded: items it would catch are rerouted to the
# default "Models & Releases" bucket (when they cannot be classified, better to
# show them than to drop them silently).
SECTION_NAMES = (
    "Models & Releases",
    "Research",
    "Business & Funding",
    "Policy & Safety",
    "Products & Tools",
    "Hardware",
)

_SENT_SPLIT = re.compile(r"(?<=[.!?])\s+")


class LLMError(Exception):
    """Raised by :class:`LLMClient` when the LLM endpoint is unreachable/errors."""


class LLMClient:
    """Minimal OpenAI-compatible ``/chat/completions`` client.

    ``transport`` has the shape ``(url, payload, headers) -> response`` and is
    injectable so the client stays unit-testable without network or API keys.
    The default is ``requests.post``.
    """

    def __init__(self, base_url: str, api_key: str | None = None, model: str | None = None,
                 transport=None, max_tokens: int | None = None):
        self.base_url = (base_url or "").rstrip("/")
        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens
        self.transport = transport

    def chat(self, system: str, user: str, **kwargs) -> str:
        """Send a system+user prompt and return the assistant message content."""
        if not self.transport:
            raise LLMError("no transport configured for LLMClient")
        payload = {
            "model": self.model or "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self.max_tokens is not None:
            payload["max_tokens"] = self.max_tokens

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        response = self.transport(f"{self.base_url}/chat/completions", payload, headers)
        if hasattr(response, "status_code"):
            if response.status_code >= 400:
                text = getattr(response, "text", "") or ""
                raise LLMError(f"HTTP {response.status_code} from {self.base_url}: {text}")
        if isinstance(response, dict) and response.get("error"):
            raise LLMError(str(response.get("error")))
        content = _extract_content(response)
        if content is None:
            raise LLMError(f"empty response from {self.base_url}")
        return content

    @staticmethod
    def _extract_content(response) -> str | None:
        if isinstance(response, str):
            return response.strip() or None
        if isinstance(response, dict):
            choices = response.get("choices")
            if isinstance(choices, list) and choices:
                message = choices[0].get("message", {}) or {}
                content = message.get("content")
                if content:
                    return content
                reasoning = message.get("reasoning_content")
                if reasoning:
                    return reasoning.strip()
            return None
        return None


def extract_bullets(text: str, limit: int = 2) -> list[str]:
    """Turn prose into up to ``limit`` sentence bullets.

    Splits on sentence terminators, trims each bullet, and caps length at 220
    chars (with a trailing ellipsis) so long source text cannot break the layout.
    """
    if not text:
        return []
    bullets = []
    for chunk in _SENT_SPLIT.split(text.strip()):
        chunk = chunk.strip()
        if not chunk:
            continue
        if len(chunk) > 220:
            chunk = chunk[:220] + "…"
        bullets.append(chunk)
        if len(bullets) >= limit:
            break
    return bullets


# Ordered keyword rules. Classification returns the first section whose rule
# matches; ordering encodes priority (e.g. funding beats "inference"/Hardware).
_KEYWORD_RULES = (
    (
        "Models & Releases",
        [
            "open-source", "opensource", "open source", "release", "releases",
            "launched", "launch", "models", "model", "gpt", "weights", "pretrained",
            "transformer", "fine-tuned", "fine tuned", "framework", "agent",
            "agents", "agentic", "openai",
        ],
    ),
    (
        "Research",
        [
            "research", "researcher", "papers", "paper", "studies", "study",
            "arxiv", "preprint", "sota", "experiment", "experiments", "scientists",
            "academic", "whitepaper", "findings",
        ],
    ),
    (
        "Business & Funding",
        [
            "startup", "ventures", "funding", "funded", "invested", "investment",
            "investor", "capital", "financ", "ipo", "acquisition", "acquire",
            "merger", "billion", "million", "dollars", "dollar", "raised", "raise",
            "raising", "revenue", "valuation", "price",
        ],
    ),
    (
        "Policy & Safety",
        [
            "regulation", "regulatory", "legislation", "legislative", "law", "legal",
            "court", "ruling", "rulings", "ban", "banned", "lawsuit", "litigation",
            "compliance", "ai act", "safety", "secure", "alignment", "oversight",
            "ethic", "privacy", "policy", "mandate", "enforce", "executive order",
            "government",
        ],
    ),
    (
        "Products & Tools",
        [
            "api", "apis", "developer", "sdk", "library", "libraries", "platform",
            "tool", "tools", "plugin", "plugins", "extension", "extensions",
            "integration", "integrations", "software", "saas",
        ],
    ),
    (
        "Hardware",
        [
            "nvidia", "intel", "amd", "chip", "chips", "gpu", "cpus", "datacenter",
            "data center", "server", "servers", "hardware", "accelerator",
            "accelerators", "semiconductor", "silicon", "inference", "rack",
        ],
    ),
)

_KEYWORD_RE = [re.compile(r"\b" + re.escape(kws[0]) + r"\b", re.IGNORECASE) for _, kws in _KEYWORD_RULES]


def classify_section(text: str) -> str:
    """Classify a title/summary into a section name.

    Returns "Other" when nothing matches. Order is the priority: the first rule
    whose keyword appears (as a whole word) wins.
    """
    for regex, section in zip(_KEYWORD_RE, SECTION_NAMES):
        if any(r.search(text or "") for r in regex):
            return section
    return "Other"


class HeuristicSummarizer:
    """Offline, deterministic summarizer: keyword classify + first-sentence bullets."""

    mode = "heuristic"

    def summarize(self, articles: list[Article]) -> Briefing:
        buckets: dict[str, list[Article]] = {name: [] for name in SECTION_NAMES}
        for article in articles:
            text = (article.title or article.summary or "").strip()
            # Items that fall through every rule are bucketed under the default
            # section rather than dropped.
            name = "Models & Releases" if classify_section(text) == "Other" else classify_section(text)
            buckets[name].append(article)

        sections: list[BriefingSection] = []
        for name in SECTION_NAMES:
            items = [
                BriefingItem(article=a, bullets=extract_bullets(a.summary) or extract_bullets(a.title))
                for a in buckets[name]
            ]
            if items:
                sections.append(BriefingSection(title=name, items=items))
        return Briefing(sections=sections, mode=self.mode)


class SummarizeAgent:
    """LLM-backed summarizer with automatic fallback to the heuristic path."""

    mode = "llm"

    def __init__(self, llm: LLMClient, system_prompt: str | None = None, max_tokens: int | None = None):
        self.llm = llm
        self.max_tokens = max_tokens if max_tokens is not None else getattr(llm, "max_tokens", 4096)
        self.system_prompt = system_prompt or self._default_system_prompt()

    def summarize(self, articles: list[Article], now: datetime | None = None) -> Briefing:
        if not articles:
            # Short-circuit: never waste an LLM round trip on nothing.
            generated = now or datetime.now(timezone.utc)
            return Briefing(sections=[], mode=self.mode, generated_at=generated)
        try:
            user = self._build_user_prompt(articles)
            raw = self.llm.chat(self.system_prompt, user)
            return self._build_from_llm(raw, articles, now=now)
        except Exception:
            # Any failure (network, timeout, bad JSON, malformed structure)
            # collapses back to the deterministic heuristic summarizer.
            return HeuristicSummarizer().summarize(articles)

    @staticmethod
    def _default_system_prompt() -> str:
        return (
            "You are a careful AI-news summarizer. Summarize ONLY the articles provided "
            "below by writing a few concise bullet points for each. Return strictly valid "
            "JSON with this shape:\n"
            '{"sections":[{"title":"Section","items":[{"ref":1,"bullets":["bullet","bullet"]}]}]}'
            "\nArticle numbering starts at 1 and must match the list below exactly. "
            "Do not invent titles, URLs, or facts."
        )

    def _build_user_prompt(self, articles: list[Article]) -> str:
        lines = [f"{i}. {a.title} | {a.url} | {a.source} | {a.summary}" for i, a in enumerate(articles, 1)]
        return "Articles:\n" + "\n".join(lines)

    def _build_from_llm(self, raw: str, articles: list[Article], now: datetime | None) -> Briefing:
        text = raw.strip()
        # Accept optional ```json code fences.
        fenced = re.search(r"```(?:json|JSON)?\s*\n?(.*?)```", text, re.DOTALL)
        data = json.loads(fenced.group(1) if fenced else text.strip())
        sections: list[BriefingSection] = []
        for sec in data.get("sections") or []:
            items_out: list[BriefingItem] = []
            for it in sec.get("items") or []:
                ref = it.get("ref")
                if not isinstance(ref, int) or ref < 1 or ref > len(articles):
                    continue
                article = articles[ref - 1]
                bullets = [
                    b for b in (it.get("bullets") or []) if isinstance(b, str) and b.strip()
                ]
                if not bullets:
                    continue
                # Cap bullet length to keep the rendered report tidy.
                items_out.append(BriefingItem(article=article, bullets=[b[:300] for b in bullets]))
            if items_out:
                sections.append(BriefingSection(title=sec.get("title", ""), items=items_out))
        return Briefing(sections=sections, mode=self.mode, generated_at=now or datetime.now(timezone.utc))


def build_summarizer(settings) -> HeuristicSummarizer | SummarizeAgent:
    """Return an LLM agent when the settings provide a usable LLM, else heuristic."""
    if not settings.has_llm:
        return HeuristicSummarizer()
    return SummarizeAgent(
        llm=LLMClient(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
        )
    )
