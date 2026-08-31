# Working notes — AI news briefing agent

## 2026-08-29 — Project scaffold + environment probe

- Goal: agentic pipeline that runs every morning, researches the latest AI news, and writes a dated markdown briefing with bullet points.
- Environment probe:
  - Network is available from this machine; all candidate RSS/Atom feeds reachable (HTTP 200) except Google Research default feed path, The Batch, DeepMind new URL, Axios (403 bot block).
  - Working feeds chosen as defaults: VentureBeat AI, Ars Technica AI, TechCrunch AI, The Verge AI (Atom), MIT Tech Review AI, OpenAI News, Google Research (Blogger feed), DeepMind blog, Hugging Face blog, AWS ML blog, Simon Willison (Atom).
  - No LLM server on the usual probe ports (8080/11434/1234/8000).
  - User clarification + pi config (~/.pi/agent/models.json): the LLM is oMLX on port 7999, reachable as `http://localhost:7999/v1` (provider m3_omlx) or `http://10.0.0.149:7999/v1` (provider m5_omlx). Both are up (HTTP 401 without key), API key is the local placeholder `local-key`, OpenAI-compatible `/v1/chat/completions`. Both hosts list `Qwen3.8-27B-4bit` (the strongest model on each).
- Consequence for design: the agent must degrade gracefully. LLM mode (OpenAI-compatible `chat/completions` on oMLX) for categorization + synthesis; deterministic heuristic fallback when the endpoint is down, so unattended cron runs never produce an empty report. Config comes from a project `.env` (small built-in loader, no extra dependency): `AI_NEWS_LLM_BASE_URL`, `AI_NEWS_LLM_API_KEY`, `AI_NEWS_LLM_MODEL`. Default sample points at `localhost:7999/v1` + `Qwen3.8-27B-4bit`; user switches the host if needed.

## 2026-08-29 — Design decisions

- Agentic but grounded: the LLM only returns structured JSON referencing article IDs and writing bullet points. Titles, URLs, dates, sources come from the feeds. This prevents the model from inventing links in an unattended morning job.
- Two summarizers behind one interface:
  - `SummarizeAgent` (LLM): prompt -> JSON `{sections: [{title, items: [{ref, bullets}]}]}`; validated refs; on any error (timeout, bad JSON) falls back to the heuristic.
  - `HeuristicSummarizer`: keyword classification into fixed sections + first-sentence extraction from feed descriptions. No network.
- Feeds parsed with stdlib `xml.etree` (RSS 2.0 + Atom) to keep dependencies light; only `requests` is a hard dependency.
- Dedup: normalized URL (lowercase host, drop fragment + tracking params) + seen-store (guid -> last seen date, pruned) so the same story is not re-briefed on consecutive runs.
- Recency window: default 26h (covers the night + morning gap); items without dates are included (most feeds are fresh) but marked `date_unknown`.
- Output: `reports/YYYY-MM-DD.md` (UTC date), atomic write (tmp + rename).
- Scheduling: `ai-news run` one-shot; cron example + macOS launchd plist in `scheduling/`.
- TDD: all tests in `tests/` written before implementation, per repo guideline.

## 2026-08-29 — Live LLM verification

- User initially said key `local_key`; server rejects it on both hosts ("Invalid API key"). User then confirmed: key is `local-key` (matches pi's `~/.pi/agent/models.json`).
- Round-trip chat completions verified with `Qwen3.8-27B-4bit` on both `localhost:7999` and `10.0.0.149:7999` (localhost ~5s; model returns `reasoning_content` + `content` — a thinking model, so budget tokens accordingly: `max_tokens` 4096 in `.env.example`).
- `.env.example` ships with `local-key` and `localhost:7999/v1` by default, `10.0.0.149:7999/v1` as a commented alternative.

## 2026-08-29 — TDD: tests first

- Wrote conftest fixtures (sample RSS + Atom feeds, fake LLM client, fake HTTP transport) plus unit tests for: feed parsing, recency filter, dedup, seen store, heuristic summarizer, LLM agent JSON handling + fallback, markdown rendering, report writing, pipeline, CLI.
- (to be appended as implementation proceeds)
