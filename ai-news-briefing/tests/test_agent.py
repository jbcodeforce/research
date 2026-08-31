"""Tests for ai_news.agent: LLM client, heuristic summarizer, agentic summarizer."""
from __future__ import annotations

from ai_news.agent import (
    HeuristicSummarizer,
    LLMClient,
    LLMError,
    SummarizeAgent,
    build_summarizer,
    classify_section,
    extract_bullets,
)
from ai_news.models import Article
from conftest import FakeLLM, LLM_VALID_JSON

import pytest


def _art(title, summary="", url=None, **kw) -> Article:
    base = dict(source="S", title=title, summary=summary, published=None)
    base.update(kw)
    return Article(url=url or f"https://x/{title.lower().replace(' ', '-')}", **base)


# ---------------------------------------------------------------- classify


@pytest.mark.parametrize(
    "text,expected",
    [
        ("Open-source model tops benchmark", "Models & Releases"),
        ("New GPT release from lab", "Models & Releases"),
        ("Research paper on reasoning", "Research"),
        ("New arxiv study shows better sota", "Research"),
        ("Startup raises a billion dollars", "Business & Funding"),
        ("EU AI Act regulation takes effect", "Policy & Safety"),
        ("Safety alignment report published", "Policy & Safety"),
        ("New developer API launches", "Products & Tools"),
        ("Nvidia ships new AI chip", "Hardware"),
        ("Datacenter buildout for inference", "Hardware"),
        ("Something ambiguous entirely", "Other"),
    ],
)
def test_classify_section(text, expected):
    assert classify_section(text) == expected


def test_classify_section_priority_business_over_hardware():
    # "inference" is a hardware keyword, but funding must win (rule order)
    assert classify_section("Startup raised a billion dollars to scale inference") == "Business & Funding"


# ---------------------------------------------------------------- bullets


def test_extract_bullets_first_sentences():
    out = extract_bullets("First fact. Second fact. Third fact.", limit=2)
    assert out == ["First fact.", "Second fact."]


def test_extract_bullets_caps_length():
    long = "a" * 500 + "."
    out = extract_bullets(long, limit=1)
    assert len(out) == 1
    assert len(out[0]) <= 220
    assert out[0].endswith("…")


def test_extract_bullets_no_period_single_chunk():
    out = extract_bullets("one long sentence without terminators", limit=2)
    assert out == ["one long sentence without terminators"]


def test_extract_bullets_empty():
    assert extract_bullets("", limit=2) == []


# ---------------------------------------------------------------- heuristic


def test_heuristic_groups_by_section():
    arts = [
        _art("Open-source model tops benchmark", "Team released an open-source model. It tops the benchmark."),
        _art("Startup raises a billion dollars", "Raised a billion dollars for inference."),
        _art("EU AI Act regulation takes effect", "The EU AI Act starts applying."),
    ]
    b = HeuristicSummarizer().summarize(arts)
    assert [s.title for s in b.sections] == [
        "Models & Releases",
        "Business & Funding",
        "Policy & Safety",
    ]
    assert b.mode == "heuristic"


def test_heuristic_sections_in_canonical_order_and_skip_empty():
    arts = [
        _art("EU AI Act regulation", "Policy text."),
        _art("New model release", "Model weights out."),
    ]
    b = HeuristicSummarizer().summarize(arts)
    titles = [s.title for s in b.sections]
    assert titles == ["Models & Releases", "Policy & Safety"]


def test_heuristic_item_bullets_from_summary():
    b = HeuristicSummarizer().summarize([_art("M", "Fact one. Fact two. Fact three.")])
    item = b.sections[0].items[0]
    assert item.article.title == "M"
    assert item.bullets == ["Fact one.", "Fact two."]


def test_heuristic_empty_input():
    b = HeuristicSummarizer().summarize([])
    assert b.sections == []


# ---------------------------------------------------------------- llm client


def _resp(content: str) -> dict:
    return {"choices": [{"message": {"content": content}}]}


def test_llm_client_posts_chat_completions():
    seen = {}

    def transport(url, payload, headers):
        seen.update(url=url, payload=payload, headers=headers)
        return _resp("pong")

    c = LLMClient(base_url="http://localhost:7999/v1", api_key="k", model="m", transport=transport)
    assert c.chat("sys", "user") == "pong"
    assert seen["url"] == "http://localhost:7999/v1/chat/completions"
    assert seen["payload"]["model"] == "m"
    assert seen["payload"]["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "user"},
    ]
    assert seen["headers"]["Authorization"] == "Bearer k"


def test_llm_client_http_error_raises_llmerror():
    def transport(url, payload, headers):
        return {"error": {"message": "boom"}}

    c = LLMClient(base_url="http://h/v1", model="m", transport=transport)
    with pytest.raises(LLMError):
        c.chat("s", "u")


def test_llm_client_bad_status_raises():
    def transport(url, payload, headers):
        class R:
            status_code = 500
            text = "err"
        return R()

    c = LLMClient(base_url="http://h/v1", model="m", transport=transport)
    with pytest.raises(LLMError):
        c.chat("s", "u")


# ---------------------------------------------------------------- agent


def test_agent_uses_llm_when_available(fake_llm):
    arts = [
        _art("Open-source model tops benchmark", "Team released an open-source model. It tops the benchmark."),
        _art("Startup raises a billion dollars", "Raised a billion."),
    ]
    b = SummarizeAgent(llm=fake_llm).summarize(arts)
    assert b.mode == "llm"
    assert len(b.sections) == 1
    item = b.sections[0].items[0]
    # ref 1 maps back to the real article (grounded: title/url from the feed)
    assert item.article.title == "Open-source model tops benchmark"
    assert item.article.url.startswith("https://x/")
    assert item.bullets == ["Released an open-source model", "Tops the benchmark"]
    # prompt carried the numbered article list
    assert "Open-source model tops benchmark" in fake_llm.calls[0]["user"]


def test_agent_falls_back_on_llm_error():
    arts = [_art("Open-source model tops benchmark", "Fact one. Fact two.")]
    b = SummarizeAgent(llm=FakeLLM(error=LLMError("timeout"))).summarize(arts)
    assert b.mode == "heuristic"
    assert b.sections[0].items[0].article.title == "Open-source model tops benchmark"


def test_agent_falls_back_on_invalid_json():
    arts = [_art("Open-source model tops benchmark", "Fact one.")]
    b = SummarizeAgent(llm=FakeLLM(content="not json at all")).summarize(arts)
    assert b.mode == "heuristic"


def test_agent_handles_json_fences():
    arts = [_art("Open-source model tops benchmark", "Fact one.")]
    fenced = "```json\n" + LLM_VALID_JSON + "\n```"
    b = SummarizeAgent(llm=FakeLLM(content=fenced)).summarize(arts)
    assert b.mode == "llm"


def test_agent_drops_out_of_range_refs():
    arts = [_art("A", "a.")]
    bad = '{"sections": [{"title": "X", "items": [{"ref": 99, "bullets": ["b"]}, {"ref": 0, "bullets": ["b2"]}, {"ref": 1, "bullets": ["b3"]}]}]}'
    b = SummarizeAgent(llm=FakeLLM(content=bad)).summarize(arts)
    assert b.mode == "llm"
    assert [it.article.title for it in b.sections[0].items] == ["A"]


def test_agent_truncates_overlong_bullets():
    arts = [_art("A", "a.")]
    long = "x" * 500
    bad = '{"sections": [{"title": "X", "items": [{"ref": 1, "bullets": ["' + long + '"]}, {"ref": 1, "bullets": []}]}]}'
    b = SummarizeAgent(llm=FakeLLM(content=bad)).summarize(arts)
    # first item kept with truncated bullet, second item (no bullets) dropped
    assert [len(it.bullets) for it in b.sections[0].items] == [1]
    assert len(b.sections[0].items[0].bullets[0]) <= 300


def test_agent_empty_articles_short_circuits():
    fake = FakeLLM()
    b = SummarizeAgent(llm=fake).summarize([])
    assert b.sections == []
    assert fake.calls == []  # no LLM round trip wasted


# ---------------------------------------------------------------- factory


def test_build_summarizer_without_llm_config_is_heuristic(tmp_path):
    from ai_news.config import Settings

    s = Settings(feeds=[], output_dir=tmp_path, state_file=tmp_path / "s.json")
    s.llm_base_url = None
    summ = build_summarizer(s)
    assert isinstance(summ, HeuristicSummarizer)


def test_build_summarizer_with_llm_config_is_agent(tmp_path):
    from ai_news.config import Settings

    s = Settings(
        feeds=[],
        output_dir=tmp_path,
        state_file=tmp_path / "s.json",
        llm_base_url="http://localhost:7999/v1",
        llm_api_key="local-key",
        llm_model="Qwen3.8-27B-4bit",
    )
    summ = build_summarizer(s)
    assert isinstance(summ, SummarizeAgent)
