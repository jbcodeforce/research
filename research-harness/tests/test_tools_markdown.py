"""Tests for the pure markdown building-block helpers."""

from research_harness.tools.markdown import (
    bold,
    code,
    code_block,
    heading,
    join,
    list_item,
    link,
    ordered_item,
    paragraph,
    table,
    toc,
)


def test_heading_levels():
    assert heading("Title") == "## Title"
    assert heading("Top", level=1) == "# Top"
    assert heading("H6", level=6) == "###### H6"


def test_heading_invalid_level():
    for level in (0, 7):
        try:
            heading("x", level=level)
        except ValueError:
            pass
        else:
            raise AssertionError(f"heading should reject level {level}")


def test_code_escapes_backticks():
    assert code("a`b") == "`a\\`b`"
    assert code("plain") == "`plain`"


def test_code_block_has_fence_and_rstrips():
    block = code_block("x\n")
    assert block == "```python\nx\n```"
    assert block.count("```") == 2


def test_code_block_defaults_to_text_language_when_empty():
    assert code_block("code", language="") == "```text\ncode\n```"


def test_list_item_and_ordered_item():
    assert list_item("x") == "- x"
    assert ordered_item("x") == "1. x"
    assert ordered_item("x", index=3) == "3. x"


def test_table_roundtrip():
    out = table(["Name", "Why"], [["pydantic", "fast"]])
    lines = out.splitlines()
    assert lines[0] == "| Name | Why |"
    assert lines[1] == "| --- | ---"
    assert lines[2] == "| pydantic | fast |"


def test_table_empty_headers():
    assert table([], [["x"]]) == ""


def test_link():
    assert link("readme", "http://x") == "[readme](http://x)"


def test_bold_wiki_text():
    assert bold("important") == "**important**"


def test_bold_refuses_banned_fragments():
    # Code/table-delimiter/quote fragments must never be wrapped in **...**
    assert bold("|a|b|") == "`|a|b|`"
    assert "**" not in bold("`code`")
    assert "**" not in bold(">quote")


def test_paragraph_passthrough():
    assert paragraph("hello") == "hello"


def test_toc_ignores_code_and_respects_start_level():
    md = "# Top\n\n## Sub\n\n```python\n# not a heading\n```\n\n### Deep"
    toc_md = toc(md, start_level=2)
    assert "[Sub](sub)" in toc_md
    assert "[Deep](deep)" in toc_md
    assert "[Top](top)" not in toc_md
    assert "not a heading" not in toc_md

    full = toc(md, start_level=1)
    assert "[Top](top)" in full



def test_toc_empty_returns_empty_string():
    assert toc("no headings here") == ""


def test_join_collapses_and_strips():
    out = join(["  a  ", "", "   ", "b"])
    assert out == "a\n\nb"
