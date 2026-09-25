"""Tests for deterministic markdown assembly in research_harness.present."""

from research_harness.state import (
    CodeResult,
    FileSpec,
    PresentationResult,
    ResearchPlan,
    TechStack,
)
from research_harness.present import (
    _anchor,
    _tree,
    build_notes,
    build_readme,
    build_root_readme_section,
    format_markdown,
)


# ---------- format_markdown ----------


def test_format_markdown_empty():
    assert format_markdown("") == ""


def test_format_markdown_closes_unclosed_fence():
    raw = "code block\n```python\nx = 1"
    out = format_markdown(raw)
    assert out.count("```python") == 1
    assert out.endswith("\n")


def test_format_markdown_closes_unclosed_fence_in_language_variants():
    raw = "```python\nx = 1\n```"
    out = format_markdown(raw)
    assert out.count("```") == 2


def test_format_markdown_collapses_triple_blank_lines():
    out = format_markdown("a\n\n\n\n\nb")
    assert "\n\n\n" not in out
    assert "a\n\nb" in out


def test_format_markdown_deduplicates_consecutive_headings():
    out = format_markdown("# Title\n# Title\ntext")
    assert out.count("# Title") == 1


def test_format_markdown_preserves_non_consecutive_headings():
    out = format_markdown("# Title\nbody\n# Sub")
    assert "# Title" in out and "# Sub" in out


def test_format_markdown_reduces_heavy_bold():
    out = format_markdown("****bold**** text")
    assert out.count("**bold**") == 1
    assert "****" not in out


def test_format_markdown_keeps_single_bold():
    assert format_markdown("**single**") == "**single**\n"


def test_format_markdown_trims_line_trailing_whitespace():
    out = format_markdown("  spaced   line  ")
    assert out.splitlines()[0].rstrip() == "  spaced   line"


# ---------- _tree ----------


def test_tree_accepts_filespec_and_uses_path():
    paths = [FileSpec(path="./src/app.py", kind="file"), FileSpec(path="./src", kind="dir")]
    out = _tree(paths, "research-harness")
    assert "app.py" in out
    assert "src" in out


def test_tree_includes_all_paths():
    out = _tree(["./src/app.py", "./docs/readme.md"], "research-harness")
    assert "app.py" in out
    assert "readme.md" in out


def test_tree_output_is_sorted():
    # Sorted output: the first emitted name comes before the second.
    out = _tree(["./b.py", "./a.py"], "root")
    lines = out.splitlines()
    names = [l.split("- ", 1)[-1].split("/", 1)[-1] for l in lines]
    assert names == sorted(names)


# ---------- _anchor ----------


def test_anchor_slugifies_topic():
    assert _anchor("Neural Weather Forecasting") == "neural-weather-forecasting"


# ---------- build_readme ----------


def _plan(topic="weather", scope="coding", success="tests pass"):
    return ResearchPlan(
        topic=topic,
        folder_name="folder",
        branch_name="branch",
        scope=scope,
        success_criteria=success,
        tech_stack=[TechStack(name="pydantic", reason="fast")],
    )


def test_build_readme_contains_sections():
    plan = _plan()
    code = CodeResult(src_files=[FileSpec(path="./src/app.py", kind="file")], observations="ok")
    presentation = PresentationResult(readme_markdown="## Summary\ndone")
    md = build_readme(plan, code, presentation)
    assert md.startswith("# weather")
    assert "Scope" in md
    assert "Tech stack" in md
    assert "pydantic" in md  # from tech stack table
    assert "src/app.py" in md  # from files tree
    assert "Summary" in md
    assert "done" in md  # presentation readme snippet
    # convention: no heavy inline bold
    assert "****" not in md


def test_build_readme_success_criteria_none():
    plan = _plan(success="")
    code = CodeResult()
    presentation = PresentationResult()
    md = build_readme(plan, code, presentation)
    assert "- None specified" in md


def test_build_readme_empty_files_tree():
    plan = _plan()
    code = CodeResult(src_files=[], observations="")
    presentation = PresentationResult()
    md = build_readme(plan, code, presentation)
    assert "Files" in md


# ---------- build_notes ----------


def test_build_notes_marked_reported_when_present():
    plan = _plan()
    code = CodeResult(src_files=[FileSpec(path="./src/app.py", kind="file")], observations="look at x")
    presentation = PresentationResult(readme_markdown="done")
    md = build_notes(plan, code, presentation)
    assert "notes: weather" in md
    assert "- [x] Reported" in md
    assert "- [x] Implemented and tested" in md
    assert "Implementation notes" in md
    assert "look at x" in md


def test_build_notes_not_reported_when_missing():
    plan = _plan()
    code = CodeResult()
    presentation = PresentationResult()
    md = build_notes(plan, code, presentation)
    assert "- [ ] Reported" in md
    assert "- [ ] Implemented and tested" in md
    assert "Implementation notes" not in md


# ---------- build_root_readme_section ----------


def test_build_root_readme_section():
    plan = _plan(topic="weather forecast", scope="coding")
    presentation = PresentationResult(readme_markdown="## Summary\nthe approach here")
    section = build_root_readme_section(plan, CodeResult(), presentation)
    assert "## weather forecast" in section
    assert "coding" in section
    assert "the approach here" in section
    assert "[README](research-harness/)" in section


def test_build_root_readme_section_truncates_long_summary():
    plan = _plan()
    presentation = PresentationResult(readme_markdown="x" * 500)
    section = build_root_readme_section(plan, CodeResult(), presentation)
    lines = section.splitlines()
    approach = lines[2]  # "- **Approach:** <snippet>"
    assert approach.endswith("...")
    assert approach.startswith("- **Approach:** ")
    assert len(approach) - len("- **Approach:** ") == 243
