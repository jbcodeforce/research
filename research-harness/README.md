# research-harness

A **lightweight Agno-based harness** that turns a natural-language research topic
into a git branch plus a nicely formatted `README.md` / `notes.md`, while following
this repo's [`AGENTS.md`](../AGENTS.md) conventions (Python + `uv`, TDD with a
separate `tests/` folder, no repo-wide dependency graph).

The idea (from the original project notes): a small, fully-deterministic core that
produces clean markdown, wrapped by LLM agents whose only job is to emit JSON that
the deterministic core parses. That split keeps the tested surface real and offline.

## Why it exists

Doing research in this monorepo means every investigation has to scaffold a branch,
write files, commit, and produce readable docs. Doing that well requires care with
markdown formatting, git quoting/branch names, and replayable tests. This harness
automates the boilerplate so a researcher can focus on the topic.

## Layout

```
research-harness/
  src/research_harness/
    config.py          # LLMConfig / HarnessConfig / ProjectConfig / RepoConventions (pure)
    state.py           # ResearchPlan / ResearchRun / CodeResult / PresentationResult + slugify
    extract.py         # find_json / model_from_json — pure, parses LLM JSON into pydantic models
    workflow.py        # build_research_workflow + run_research + the Agno Workflow orchestration
    present.py         # build_readme / build_notes / build_root_readme_section / format_markdown
    tools/{repo,shell,markdown}.py
    tools/stub.py      # StubModel / SequenceModel — canned responses, no network
    agents/{factory,researcher,coder,reporter}.py
  tests/               # pytest suite (see below)
```

## Pipeline

An Agno `Workflow` orchestrates four steps:

1. **plan** (researcher agent) → JSON describing the topic, folder, branch, tech stack.
2. **scaffold** (deterministic executor) → creates the git branch and the project folder.
3. **code** (coder agent) → JSON describing source/test files, run command, observations.
4. **present** (reporter agent) → JSON describing `notes.md`, the project `README.md`, and the root-README index section.

`run_research(topic, config, model=None, stub_responses=None)` runs it and assembles a
`ResearchRun`. When `model` is `None`, a real OpenAI-compatible model is built (works
with local OMLX/Ollama). For tests, pass a stub model so the whole thing runs offline.

The deterministic parsing (`_collect_structured`) matches each step's JSON to the schema
whose declared field names appear most often in it (at least `_MIN_STEP_KEYS`). The
markdown normalization (`format_markdown`) enforces the repo's "avoid heavy **bold**"
rule, dedups headings, fixes unclosed code fences, and builds a table of contents.

## Offline testing (TDD)

The harness is designed to be fully testable without an LLM. Each deterministic
function is pure and unit-tested; the workflow is exercised end-to-end with a stub model.

```bash
cd research-harness
uv sync
uv run pytest          # 73 passing
```

Tests:

- `test_extract.py` (15) — JSON finding + pydantic parsing.
- `test_state.py` (12) — slugify, `ResearchPlan` validation, `FileSpec`/`TechStack` coercion.
- `test_present.py` (20) — `format_markdown`, `_tree`, README/notes/root-section builders.
- `test_tools_markdown.py` (15) — markdown helpers (bold refusal, tables, ToC, fences).
- `test_workflow.py` (8) — `_content_of`, `_collect_structured` schema matching.
- `test_integration.py` (3) — full offline `run_research` on a real git repo: branch,
  commit, project deliverables, root README update.

## Real LLM vs stub

- **Stub** (`tools/stub.py`): a non-LLM `Model` returning canned content, never emitting
  tool calls. `SequenceModel` pops one distinct response per call so each workflow step
  can be driven deterministically.
- **Real**: `build_model(config, ...)` builds an OpenAI-compatible chat model from
  `LLMConfig` (which reads `.env`, defaulting to a local endpoint). Wiring a real model
  in needs only an API key / base URL; the workflow and parsing stay identical.

## Bugs found and fixed

This investigation also fixed two real defects:

1. **Root README section written to the wrong path.** `_finalize` wrote the root-README
   index into `project_path / folder_name` (clobbering the project README and landing the
   section in the wrong place). It now writes to `git_root / README.md`, and all agents,
   the scaffold, and `_finalize` operate consistently within `config.project_path` (the
   previous `config.root`-vs-`folder_name` nesting produced `<root>/<slug>/<slug>/...`).
2. **Embedded newlines broke JSON parsing.** Canned/reporter JSON values such as
   `## Notes\ncontent` contain newlines. An unescaped real newline is invalid JSON, so
   `find_json` rejected the whole blob and the presentation artefact silently failed to
   parse. Fixed the fixtures with valid `\n` escapes and added a regression test.

See [`notes.md`](notes.md) for the full trail.

## Scope

Light by design: three LLM agents, one deterministic executor, one deterministic
formatter, one git commit. No database, no remote services, no multi-agent fan-out.
