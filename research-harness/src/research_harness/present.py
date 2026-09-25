"""Deterministic markdown assembly and normalization.

This is the *light* but high-value part of the harness: no matter what the LLM
agents produce, :func:`format_markdown` enforces this repo's markdown convention
(*avoid heavy inline bold*) and valid fenced code blocks. It also builds the
README / notes / root-README sections from structured state so output is always
well-formed. Everything here is pure and unit tested.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, List, Union

from research_harness.state import (
    CodeResult,
    FileSpec,
    PresentationResult,
    ResearchPlan,
)
from research_harness.tools.markdown import code, code_block, heading, table

REPO_URL = os.getenv("RESEARCH_REPO_URL", "")


def _tree(paths: Iterable[Union[str, FileSpec]], root: str) -> str:
    """Render a minimal source-tree from relative file paths.

    Accepts either plain path strings or :class:`FileSpec` objects (uses their
    ``.path``).
    """
    lines: List[str] = []
    prefixes: List[str] = [root.rstrip("/")]
    for rel in sorted(p.path if isinstance(p, FileSpec) else p for p in paths):
        full = rel if rel.startswith("./") else "./" + rel
        common = ""
        for pref in prefixes:
            if full == pref or full.startswith(pref.rstrip("/") + "/"):
                common = pref.rstrip("/") + "/"
                break
        rel_key = full[len(common) :]
        if "/" in rel_key:
            prefix, name = rel_key.split("/", 1)
            prefixes.append(common + prefix.rstrip("/") + "/")
        else:
            name = rel_key
        indent = "    " * rel_key.count("/")
        lines.append(f"{indent}- {name}")
    return "\n".join(lines)


def format_markdown(raw: str, reduce_bold: bool = True) -> str:
    """Normalize raw LLM markdown into well-formed, convention-compliant text.

    - Deduplicates consecutive headings of the same level.
    - Ensures fenced code blocks are properly closed.
    - Reduces suspicious inline-bold runs (enforcing the *avoid heavy bold*
      convention from AGENTS.md) by collapsing ``**``/``***``/``****`` clusters.
    - Collapses 3+ consecutive blank lines to exactly two.
    - Ensures the text ends with a single trailing newline.
    """
    if not raw:
        return ""
    text = raw

    # 1. Collapse 3+ blank lines down to two (markdown paragraph break).
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 2. Close unclosed code fences.
    text = re.sub(r"(```python)(.*?)(```|$)", lambda m: f"```python\n{m.group(2).rstrip()}\n```", text, flags=re.DOTALL)

    # 3. Deduplicate consecutive identical headings.
    lines = text.split("\n")
    cleaned: List[str] = []
    last_heading: str | None = None
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            cleaned.append(line)
            continue
        if in_code:
            cleaned.append(line)
            continue
        if re.match(r"^(#{1,6})\s+\S", line):
            h = line.strip()
            if h != last_heading:
                cleaned.append(h)
                last_heading = h
            continue
        cleaned.append(line)
    text = "\n".join(cleaned)

    # 4. Reduce heavy inline bold. Collapse any run of 2+ back-to-back
    #    ``**``/``***``/``****`` openers (or closers) into a single ``**``.
    if reduce_bold:
        text = re.sub(r"\*\*\*\*", "**", text)
        text = re.sub(r"\*\*\*\*", "**", text)
        text = re.sub(r"\*\*\*\*\*", "**", text)
        text = re.sub(r"\*\*\*\*\*\*", "**", text)

    # 5. Normalize trailing whitespace on each line.
    text = "\n".join(line.rstrip() for line in text.split("\n"))

    return text.rstrip() + "\n"


def _tech_stack_table(plan: ResearchPlan) -> str:
    rows = [[ts.name, ts.reason] for ts in plan.tech_stack]
    return table(["Technology", "Why"], rows)


def build_readme(plan: ResearchPlan, code: CodeResult, presentation: PresentationResult) -> str:
    """Assemble a polished ``README.md`` for a project from structured state."""
    md = []
    title = f"# {plan.topic}"
    if REPO_URL:
        title = heading(f"[{plan.topic}]({REPO_URL})", level=1)
    md.append(title)

    toc_lines = [
        heading("Table of contents", level=2),
        "- [Scope](#scope)",
        "- [Hypothesis](#hypothesis)",
        "- [Tech stack](#tech-stack)",
        "- [Files](#files)",
        "- [Summary](#summary)",
    ]
    md.append("\n".join(toc_lines))

    md.append("")
    md.append(heading("Scope", level=2) + (f"\n\n{plan.scope}\n" if plan.scope else ""))

    md.append(heading("Hypothesis", level=2) + (f"\n\n{plan.hypothesis}\n" if plan.hypothesis else ""))

    md.append(heading("Tech stack", level=2))
    md.append(_tech_stack_table(plan))

    md.append(heading("Files", level=2))
    md.append(_tree(code.src_files, "research-harness"))

    md.append(heading("Summary", level=2))
    summary = presentation.readme_markdown.strip()
    md.append(f"\n{summary}\n" if summary else "")

    md.append(heading("Success criteria", level=2))
    md.append(f"- {plan.success_criteria}" if plan.success_criteria else "- None specified")
    md.append("")

    return format_markdown("\n".join(md))


def build_notes(plan: ResearchPlan, code: CodeResult, presentation: PresentationResult) -> str:
    """Assemble the ``notes.md`` skeleton for the project."""
    md = []
    md.append(heading(f"notes: {plan.topic}", level=1))
    md.append("")
    md.append(heading("Timeline", level=2))
    md.append("- [ ] Planned")
    md.append("- [ ] Scaffolded")
    if code.src_files:
        md.append("- [x] Implemented and tested")
    else:
        md.append("- [ ] Implemented and tested")
    if presentation.readme_markdown:
        md.append("- [x] Reported")
    else:
        md.append("- [ ] Reported")

    if code.observations:
        md.append("")
        md.append(heading("Implementation notes", level=2))
        md.append(code.observations)

    return format_markdown("\n".join(md))


def build_root_readme_section(
    plan: ResearchPlan, code: CodeResult, presentation: PresentationResult, repo_url: str = ""
) -> str:
    """Assemble the index section for the repo root ``README.md``."""
    if repo_url:
        link_text = f"[{plan.topic}]({repo_url}#{_anchor(plan.topic)})"
    else:
        link_text = plan.topic
    summary = presentation.readme_markdown.strip() if presentation.readme_markdown else ""
    summary_snippet = summary[:240] + ("..." if len(summary) > 240 else "")
    lines = [
        f"## {link_text}",
        f"- **Intent & scope:** {plan.scope or 'N/A'}",
        f"- **Approach:** {summary_snippet}",
        f"- **Read more:** [README](research-harness/)",
        "",
    ]
    return "\n".join(lines)


def _anchor(topic: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", topic.lower()).strip("-")
