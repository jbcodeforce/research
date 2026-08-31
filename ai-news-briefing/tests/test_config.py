"""Tests for ai_news.config: defaults, JSON config, .env loading, env overrides."""
from __future__ import annotations

from ai_news.config import (
    Settings,
    default_settings,
    load_settings,
    load_dotenv_file,
    project_root,
)


def test_project_root_points_at_repo_dir():
    root = project_root()
    assert root.name == "ai-news-briefing"
    assert (root / "config" / "sources.json").is_file()


def test_default_settings_have_eleven_feeds():
    s = default_settings()
    assert len(s.feeds) == 11
    assert all(f.url.startswith("https://") for f in s.feeds)
    assert s.window_hours == 26
    assert s.max_items == 40


def test_default_settings_output_paths(tmp_path):
    s = default_settings(output_dir=tmp_path / "reports", state_file=tmp_path / "seen.json")
    assert s.output_dir == tmp_path / "reports"
    assert s.state_file == tmp_path / "seen.json"


def test_load_settings_from_json_file(tmp_path):
    cfg = tmp_path / "sources.json"
    cfg.write_text(
        '{"feeds": [{"name": "Only", "url": "https://only.example.com/feed"}]}'
    )
    s = load_settings(config_path=cfg)
    assert [f.name for f in s.feeds] == ["Only"]


def test_load_settings_missing_file_falls_back_to_defaults(tmp_path):
    s = load_settings(config_path=tmp_path / "nope.json")
    assert len(s.feeds) == 11


def test_load_settings_bad_json_falls_back_to_defaults(tmp_path):
    cfg = tmp_path / "bad.json"
    cfg.write_text("{not json")
    s = load_settings(config_path=cfg)
    assert len(s.feeds) == 11


def test_load_settings_env_overrides(tmp_path, monkeypatch):
    cfg = tmp_path / "sources.json"
    cfg.write_text(
        '{"feeds": [{"name": "Only", "url": "https://only.example.com/feed"}]}'
    )
    monkeypatch.setenv("AI_NEWS_WINDOW_HOURS", "12")
    monkeypatch.setenv("AI_NEWS_MAX_ITEMS", "5")
    monkeypatch.setenv("AI_NEWS_LLM_BASE_URL", "http://localhost:7999/v1")
    monkeypatch.setenv("AI_NEWS_LLM_API_KEY", "local-key")
    monkeypatch.setenv("AI_NEWS_LLM_MODEL", "Qwen3.8-27B-4bit")
    s = load_settings(config_path=cfg, env=None)
    assert s.window_hours == 12
    assert s.max_items == 5
    assert s.llm_base_url == "http://localhost:7999/v1"
    assert s.llm_api_key == "local-key"
    assert s.llm_model == "Qwen3.8-27B-4bit"


def test_settings_has_llm():
    off = Settings(feeds=[])
    assert not off.has_llm
    on = Settings(feeds=[], llm_base_url="http://localhost:7999/v1", llm_model="m")
    assert on.has_llm
    # base url alone is not enough: model is required
    partial = Settings(feeds=[], llm_base_url="http://localhost:7999/v1")
    assert not partial.has_llm


def test_load_dotenv_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("AI_NEWS_WINDOW_HOURS=8\nAI_NEWS_TEST_FLAG=yes\n")
    loaded = load_dotenv_file(env_file)
    assert loaded == {"AI_NEWS_WINDOW_HOURS": "8", "AI_NEWS_TEST_FLAG": "yes"}


def test_load_dotenv_file_missing_is_empty():
    import os

    from ai_news.config import project_root as pr

    assert load_dotenv_file(pr() / "definitely-not-here.env") == {}
    # and it must not clobber the real environment
    assert "AI_NEWS_TEST_FLAG" not in os.environ
