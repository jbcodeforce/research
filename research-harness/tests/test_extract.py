"""Tests for JSON extraction helpers in research_harness.extract."""

from pydantic import BaseModel

from research_harness.extract import find_json, model_from_json


class Widget(BaseModel):
    name: str
    qty: int = 0


class Foo(BaseModel):
    a: int


class Bar(BaseModel):
    b: int


def test_find_json_plain():
    assert find_json('{"a":1}') == {"a": 1}


def test_find_json_ignores_leading_prose():
    text = "Here is the plan:\n\n```json\n{\"a\": 2}\n```\nDone."
    assert find_json(text) == {"a": 2}


def test_find_json_fenced_block():
    text = "```json\n{\"a\": 3}\n```"
    assert find_json(text) == {"a": 3}


def test_find_json_empty_string():
    assert find_json("") is None
    assert find_json("   ") is None


def test_find_json_no_json():
    assert find_json("no json here at all") is None


def test_find_json_accepts_dict_passthrough():
    assert find_json({"a": 5}) == {"a": 5}


def test_find_json_accepts_model_dump():
    assert find_json(Widget(name="x")) == {"name": "x", "qty": 0}


def test_find_json_none():
    assert find_json(None) is None


def test_find_json_first_invalid_brace_fragment_returns_none():
    # The first {...} fragment is incomplete, so brace-matching gives up.
    text = "a { \"b\" } then {\"a\": 4}"
    assert find_json(text) is None


def test_model_from_json_valid():
    result = model_from_json(Foo, '{"a": 7}')
    assert result is not None
    assert result.a == 7


def test_model_from_json_missing_required_field():
    # a is required; empty dict fails validation -> None
    assert model_from_json(Foo, "{}") is None


def test_model_from_json_no_json_returns_none():
    assert model_from_json(Foo, "just text") is None


def test_model_from_json_invalid_type():
    assert model_from_json(Foo, '{"a": "not-an-int"}') is None


def test_model_from_json_coerces_nested_object():
    result = model_from_json(Widget, '{"name": "gadget", "qty": 3}')
    assert result is not None
    assert result.name == "gadget"
    assert result.qty == 3


def test_model_from_json_ignores_extra_fields():
    result = model_from_json(Foo, '{"a": 1, "extra": "ignored"}')
    assert result is not None and result.a == 1
