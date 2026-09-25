"""Offline stub models so the workflow can be tested without an LLM.

These return canned content and never emit tool calls. The workflow harness
parses any returned JSON with its own pure helpers (:mod:`research_harness.extract`).
"""

from __future__ import annotations

from typing import List

from agno.models.base import Model
from agno.models.response import ModelResponse


class StubModel(Model):
    """A non-LLM model that returns the same canned content every call."""

    def __init__(self, response: str, **kwargs):
        super().__init__(id="stub", name="stub", **kwargs)
        self._response = response

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(content=self._response)

    def invoke_stream(self, *args, **kwargs):  # pragma: no cover - not exercised by sync path
        yield ModelResponse(content=self._response)

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(content=self._response)

    async def ainvoke_stream(self, *args, **kwargs):  # pragma: no cover - not exercised by sync path
        yield ModelResponse(content=self._response)

    def _parse_provider_response(self, *args, **kwargs):  # pragma: no cover - overridden
        raise NotImplementedError

    def _parse_provider_response_delta(self, *args, **kwargs):  # pragma: no cover - overridden
        raise NotImplementedError


class SequenceModel(Model):
    """A non-LLM model that pops a distinct canned response per call.

    Lets tests drive one response per workflow step (researcher/coder/reporter).
    """

    def __init__(self, responses: List[str], **kwargs):
        super().__init__(id="sequence", name="sequence", **kwargs)
        self._responses = list(responses)

    def _next(self) -> str:
        if not self._responses:
            raise RuntimeError("no stub responses left")
        return self._responses.pop(0)

    def invoke(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(content=self._next())

    def invoke_stream(self, *args, **kwargs):  # pragma: no cover - not exercised by sync path
        yield ModelResponse(content=self._next())

    async def ainvoke(self, *args, **kwargs) -> ModelResponse:
        return ModelResponse(content=self._next())

    async def ainvoke_stream(self, *args, **kwargs):  # pragma: no cover - not exercised by sync path
        yield ModelResponse(content=self._next())

    def _parse_provider_response(self, *args, **kwargs):  # pragma: no cover - overridden
        raise NotImplementedError

    def _parse_provider_response_delta(self, *args, **kwargs):  # pragma: no cover - overridden
        raise NotImplementedError
