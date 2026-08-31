"""Tests for ai_news.cli: run / list-sources / test-llm commands."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from ai_news import cli

NOW = datetime(2026, 8, 30, 7, 0, tzinfo=timezone.utc)

CLI_RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>F</title>
<item>
  <title>Model release</title>
  <link>https://n.example.com/release</link>
  <pubDate>Fri, 29 Aug 2026 20:00:00 +0000</pubDate>
  <description>Lab released a new model.</description>
</item>
</channel></rss>
"""


def _transport(url: str) -> bytes:
    if url == "https://ok.example.com/feed":
        return CLI_RSS
    raise TimeoutError(f"no route to {url}")


@pytest.fixture
def run_env(tmp_path, monkeypatch):
    """Isolated config: one feed, tmp outputs, no .env interference."""
    cfg = tmp_path / "sources.json"
    cfg.write_text(json.dumps({"feeds": [{"name": "Good", "url": "https://ok.example.com/feed"}]}))
    monkeypatch.setenv("AI_NEWS_CONFIG", str(cfg))
    monkeypatch.setenv("AI_NEWS_OUTPUT_DIR", str(tmp_path / "reports"))
    monkeypatch.setenv("AI_NEWS_STATE_FILE", str(tmp_path / "seen.json"))
    for var in ("AI_NEWS_LLM_BASE_URL", "AI_NEWS_LLM_API_KEY", "AI_NEWS_LLM_MODEL"):
        monkeypatch.delenv(var, raising=False)
    return tmp_path


def test_run_writes_report_and_prints_path(run_env, capsys, monkeypatch):
    monkeypatch.setattr(cli, "run_pipeline", lambda **kw: kw["settings"].output_dir / "2026-08-30.md")
    rc = cli.main(["run", "--config", str(run_env / "sources.json"), "--no-llm"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "2026-08-30.md" in out


def test_run_forces_date_for_backfill(run_env, capsys, monkeypatch):
    captured = {}

    def fake_pipeline(**kw):
        captured.update(kw)
        return kw["settings"].output_dir / "2026-08-01.md"

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    rc = cli.main(["run", "--date", "2026-08-01", "--no-llm"])
    assert rc == 0
    # the fixed date must anchor the run (UTC midnight)
    assert captured["now"] == datetime(2026, 8, 1, tzinfo=timezone.utc)


def test_run_window_and_max_items_flags(run_env, capsys, monkeypatch):
    captured = {}

    def fake_pipeline(**kw):
        captured.update(kw)
        return kw["settings"].output_dir / "r.md"

    monkeypatch.setattr(cli, "run_pipeline", fake_pipeline)
    cli.main(["run", "--no-llm", "--window-hours", "12", "--max-items", "5"])
    assert captured["settings"].window_hours == 12
    assert captured["settings"].max_items == 5


def test_list_sources(run_env, capsys):
    rc = cli.main(["list-sources"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Good" in out
    assert "https://ok.example.com/feed" in out


def test_test_llm_success(run_env, capsys, monkeypatch):
    calls = {}

    def fake_build(settings, **kw):
        class C:
            def chat(self, system, user):
                calls["ok"] = True
                return "pong"

        return C()

    monkeypatch.setattr(cli, "build_llm_client", fake_build)
    monkeypatch.setenv("AI_NEWS_LLM_BASE_URL", "http://localhost:7999/v1")
    monkeypatch.setenv("AI_NEWS_LLM_API_KEY", "local-key")
    monkeypatch.setenv("AI_NEWS_LLM_MODEL", "Qwen3.8-27B-4bit")
    rc = cli.main(["test-llm"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "pong" in out
    assert calls.get("ok")


def test_test_llm_failure_exit_code(run_env, capsys, monkeypatch):
    from ai_news.agent import LLMClient

    def boom(url, payload, headers):
        raise ConnectionError("connection refused")

    monkeypatch.setattr(cli, "build_llm_client", lambda s: LLMClient(
        base_url="http://localhost:7999/v1", api_key="k", model="m", transport=boom
    ))
    monkeypatch.setenv("AI_NEWS_LLM_BASE_URL", "http://localhost:7999/v1")
    monkeypatch.setenv("AI_NEWS_LLM_API_KEY", "local-key")
    monkeypatch.setenv("AI_NEWS_LLM_MODEL", "Qwen3.8-27B-4bit")
    rc = cli.main(["test-llm"])
    assert rc == 1


def test_test_llm_without_config(run_env, capsys):
    rc = cli.main(["test-llm"])
    assert rc == 1
    assert "not configured" in capsys.readouterr().out.lower()
