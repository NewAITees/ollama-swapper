# Tests for proxy helpers.
# Usage: pytest tests/test_proxy.py
import asyncio
import json

import pytest

from ollama_swapper.proxy import _stream_openai_chat, _stream_openai_generate, parse_listen


def test_parse_listen_parses_host_port() -> None:
    parsed = parse_listen("127.0.0.1:11434")
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 11434


def test_parse_listen_requires_port() -> None:
    with pytest.raises(ValueError):
        parse_listen("127.0.0.1")


class _FakeOpenAIResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    async def aiter_lines(self) -> object:
        for line in self._lines:
            yield line


async def _collect_async(iterator: object) -> list[bytes]:
    return [chunk async for chunk in iterator]


def test_stream_openai_chat_to_ollama_ndjson() -> None:
    payload = {"choices": [{"delta": {"content": "こんにちは"}}]}
    lines = [
        f"data: {json.dumps(payload)}",
        "data: [DONE]",
    ]
    response = _FakeOpenAIResponse(lines)

    chunks = asyncio.run(_collect_async(_stream_openai_chat(response, "nemotron-jp")))
    decoded = [chunk.decode("utf-8").strip() for chunk in chunks]

    assert decoded[0] == json.dumps(
        {
            "model": "nemotron-jp",
            "message": {"role": "assistant", "content": "こんにちは"},
            "done": False,
        }
    )
    assert decoded[1] == json.dumps({"model": "nemotron-jp", "done": True})


def test_stream_openai_generate_to_ollama_ndjson() -> None:
    payload = {"choices": [{"text": "hello"}]}
    lines = [
        f"data: {json.dumps(payload)}",
        "data: [DONE]",
    ]
    response = _FakeOpenAIResponse(lines)

    chunks = asyncio.run(
        _collect_async(_stream_openai_generate(response, "nemotron-jp"))
    )
    decoded = [chunk.decode("utf-8").strip() for chunk in chunks]

    assert decoded[0] == json.dumps(
        {
            "model": "nemotron-jp",
            "response": "hello",
            "done": False,
        }
    )
    assert decoded[1] == json.dumps({"model": "nemotron-jp", "done": True})
