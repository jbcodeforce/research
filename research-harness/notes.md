# notes.md

## Investigation log — Agentic research harness (light pi.dev harness)

Goal: build a lightweight Agno "harness" that formalizes the per-research
workflow described in AGENTS.md, as a multi-agent `agno.Workflow` specialized
for producing research in this repository with nice-looking markdown.

### Repo conventions that the harness must follow (from AGENTS.md)
- Python default; every Python project managed with `uv`.
- Layout: `src/<package>/`, `tests/`, `pyproject.toml` (hatchling), console
  script under `[project.scripts]`, pytest with `testpaths = ["tests"]`.
- TDD: unit tests first in a separate `tests/` folder; shared logic in common
  utilities rather than duplication.
- Commit only the project folder + the code/notes/README produced.
- Markdown: avoid heavy inline **bold** (reads AI-generated). Use headings,
  tables, code fences.

### Agno API discovery (v3.0.11 locked via `uv.lock`)
- Installed `agno>=3.0,<4` + `openai`. `uv` resolved **3.0.11**.
- Note: `flink-statement-troubleshooting` pins agno **2.6.11**; this new
  project is a separate project with its own venv, so 3.x is fine and gives the
  canonical `agno.workflow` API (Workflow, Step, Steps, Parallel, Condition).
- Key contract found (verified by introspection + a quick end-to-end test):
  - `Step` can take `agent=`, `team=`, `workflow=`, or `executor=` (a plain
    function). A function executor receives `(step_input: StepInput,
    run_context=None)` and returns `str` / `dict` (keyed by `"content"`) /
    `RunOutput` / anything (str()-ified).
  - Data passes between steps via `StepInput.previous_step_content` and
    `previous_step_outputs`; structured output is re-fed to the next step.
  - `Workflow.run(input=..., session_state=...) -> WorkflowRunOutput`
    (a dataclass with `status: RunStatus`, `content`, `step_results`).
  - Abstract model base is `agno.models.base.Model`; abstract methods are
    `invoke`, `ainvoke`, `invoke_stream`, `ainvoke_stream`,
    `_parse_provider_response`, `_parse_provider_response_delta`.
    Verified a stub model works end-to-end with `Agent` and with `Workflow`.
- Verified design: `Step(executor=...)` runs deterministically; `Step(agent=...)`
  runs the LLM; final step's `content` becomes `WorkflowRunOutput.content`.

### Design decisions
- **Orchestrator = the Agno Workflow** (3 agent steps: plan → code → present,
  + a deterministic `scaffold` step and a deterministic `format` step).
- **Guarantee nice markdown deterministically**: the LLM agents produce raw
  markdown, then a pure, fully-tested `present.format_markdown()` normalizes it
  (dedup headings, enforce the "avoid heavy bold" rule, normalize code fences,
  build a ToC). This removes dependence on LLM output quality.
- **Deterministic core is the tested part** (no LLM required):
  `tools/markdown.py`, `tools/repo.py`, `present.py`, `state.py`, `config.py`.
- **Offline tests** use a stub `Model` (canned content, no tool calls) so the
  whole Agno workflow runs without network/API keys.
- Real LLM path: OpenAI-compatible model (works with local OMLX endpoint too).

### Files planned
- `config.py`, `state.py`, `tools/{repo,shell,markdown}.py`,
  `agents/{factory,researcher,coder,reporter}.py`, `workflow.py`,
  `present.py`, `pipeline.py`, `research_cli.py`.

### Open questions
- OMLX provider base_url/key naming for a real local run (config reads env,
  defaults documented in `.env.example`).
- Keep it light: 3 agents, no DB, no remote.

## Test suite (TDD per AGENTS.md) — 73 passing
Added `tests/test_integration.py` (3 tests) covering the full offline workflow:
- `test_run_research_offline_end_to_end` — spins up a real git repo +
  `ProjectConfig`, runs `run_research(topic, config, model=SequenceModel([plan,
  code, present]))`, then asserts status==FINALIZE, plan/code/presentation parsed,
  a git branch + commit exist, and README.md/notes.md (project) and the root
  README section are written.
- `test_run_research_returns_research_run` — asserts the returned object is a
  `ResearchRun`.
- `test_pres_json_is_valid_json` — guards that the canned JSON is real JSON.
Other test files: test_extract.py (15), test_state.py (12), test_present.py (20),
test_tools_markdown.py (15), test_workflow.py (8). All green with `uv run pytest`.

### Bug fixed: project README section was written to the wrong path
`_finalize` wrote the root-README index into `project_path / folder_name` instead
of `git_root`, which both clobbered the project README and put the section in the
wrong place. Also `build_research_workflow` used `config.root` while `_finalize`
and `ResearchRun.project_path` use `config.project_path` — that inconsistent
`folder_name` nesting meant the committed deliverables lived at
`<root>/<slug>/<slug>/README.md`. Fixed so agents, scaffold, and `_finalize` all
operate within `config.project_path`, and the root README section goes to
`git_root/README.md`. The integration test asserts `config.project_path/README.md`,
`config.project_path/notes.md`, and `config.repo_root/README.md`.

### Bug fixed: embedded newlines in JSON break parsing
The reporter's README values (`## Notes\ncontent`, `## Presentation\nsummary`)
contain newlines. A JSON string value must escape them as `\n`; an unescaped real
newline makes `find_json` fail (JSONDecodeError: invalid control character), so
the presentation artefact silently failed to parse. Guarded the test fixtures
with valid escapes and added `test_pres_json_is_valid_json`.

### Lessons
- `test_workflow.py`'s `_collect_structured` matches a step to the schema with the
  most of its declared field names present (>= `_MIN_STEP_KEYS`); verify by
  dumping the per-step `data` dict and overlaps rather than trusting step order.
