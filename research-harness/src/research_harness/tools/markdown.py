"""Pure markdown building blocks.

Every function here is deterministic and side-effect free so it can be unit
tested without touching the filesystem or an LLM. The suite also enforces this
repo's convention (see AGENTS.md): *avoid heavy inline ``**bold**``* — we make
it trivial to write good markdown by providing typed helpers and by
normalizing the result in :mod:`research_harness.present`.
"""

from __future__ import annotations

from typing import List

# Fragment sizes that must never be bolded, so heavy ``**`` never sneaks in.
_NO_BOLD_FRAGMENT = ("`", "|", ">")


def _escape_code(text: str) -> str:
    """Escape backticks inside inline code so they do not terminate the fence."""
    return text.replace("\\", "\\\\").replace("`", "\\`")


def heading(text: str, level: int = 2) -> str:
    """Return a heading, e.g. ``heading('Foo', level=2) -> '## Foo'``."""
    if level < 1 or level > 6:
        raise ValueError(f"heading level must be 1-6, got {level}")
    return "#" * level + " " + text


def code(text: str, language: str = "python") -> str:
    """Return an inline code fragment: ```text``` with backticks escaped."""
    return f"`{_escape_code(text)}`"


def code_block(text: str, language: str = "python") -> str:
    """Return a fenced code block with an optional language tag."""
    language = language or "text"
    text = text.rstrip("\n")
    return f"```{language}\n{text}\n```"



def list_item(text: str) -> str:
    """Return a bullet list item."""
    return f"- {text}"


def ordered_item(text: str, index: int = 1) -> str:
    """Return an ordered list item."""
    return f"{index}. {text}"


def table(headers: List[str], rows: List[List[str]]) -> str:
    """Return a simple aligned markdown table.

    ``headers`` is the first row; ``rows`` is a list of rows.
    """
    if not headers:
        return ""
    text = f"| {' | '.join(headers)} |\n"
    text += f"| {' | '.join(['---'] * len(headers))}\n"
    for row in rows:
        text += f"| {' | '.join(row)} |\n"
    return text


def link(text: str, url: str) -> str:
    """Return an inline link: ``[text](url)``."""
    return f"[{text}]({url})"


def bold(text: str) -> str:
    """Return bold text, but refuse to emit ``**`` around banned fragments."""
    if any(fragment in text for fragment in _NO_BOLD_FRAGMENT):
        # Never bold a URL, a code fragment or a table delimiter.
        return code(text)
    return f"**{text}**"


def paragraph(text: str) -> str:
    """Return a plain paragraph line."""
    return text


def toc(markdown: str, start_level: int = 2) -> str:
    """Return a table-of-contents section for the given markdown.

    Scans the document for headings at or above ``start_level`` and emits an
    anchor list. Headings inside fenced code blocks are ignored.
    """
    lines = markdown.splitlines()
    anchors: List[str] = []
    in_code = False
    for line in lines:
        if line.strip().startswith("```"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if not line.startswith(("#", "##", "###", "####", "#####", "######")):
            continue
        level = len(line) - len(line.lstrip("#"))
        if level < start_level:
            continue
        text = line.lstrip("#").strip()
        anchor = "".join(c.lower() for c in text if c.isalnum() or c == "-")
        anchors.append(f"- [{text}]({anchor})")
    if not anchors:
        return ""
    return "## Table of contents\n\n" + "\n".join(anchors) + "\n"


def join(lines: List[str]) -> str:
    """Join non-empty lines with a single blank line between blocks."""
    return "\n\n".join(line.strip() for line in lines if line.strip())
