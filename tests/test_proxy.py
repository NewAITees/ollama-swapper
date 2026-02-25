# Tests for proxy helpers.
# Usage: pytest tests/test_proxy.py
import asyncio
import json

import pytest

from ollama_swapper.proxy import (
    _ollama_chat_to_openai,
    _openai_chat_to_ollama,
    _stream_openai_chat,
    _stream_openai_generate,
    parse_listen,
)


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
    assert decoded[1] == json.dumps(
        {"model": "nemotron-jp", "message": {"role": "assistant", "content": ""}, "done": True}
    )


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


# --- _ollama_chat_to_openai ---

def test_ollama_chat_to_openai_passes_tools() -> None:
    tools = [{"type": "function", "function": {"name": "fn", "parameters": {}}}]
    result = _ollama_chat_to_openai({"model": "m", "messages": [], "tools": tools})
    assert result["tools"] == tools


def test_ollama_chat_to_openai_passes_think() -> None:
    result = _ollama_chat_to_openai({"model": "m", "messages": [], "think": True})
    assert result["enable_thinking"] is True


def test_ollama_chat_to_openai_no_tools_key_when_absent() -> None:
    result = _ollama_chat_to_openai({"model": "m", "messages": []})
    assert "tools" not in result
    assert "enable_thinking" not in result


# --- _openai_chat_to_ollama ---

def test_openai_chat_to_ollama_converts_tool_calls() -> None:
    openai_resp = {
        "choices": [{
            "message": {
                "content": "",
                "tool_calls": [{
                    "id": "call_1",
                    "type": "function",
                    "function": {"name": "get_weather", "arguments": '{"location": "Tokyo"}'},
                }],
            }
        }]
    }
    result = _openai_chat_to_ollama(openai_resp, "m")
    tc = result["message"]["tool_calls"]
    assert tc[0]["function"]["name"] == "get_weather"
    assert tc[0]["function"]["arguments"] == {"location": "Tokyo"}


def test_openai_chat_to_ollama_converts_reasoning_content() -> None:
    openai_resp = {
        "choices": [{
            "message": {"content": "answer", "reasoning_content": "step by step"},
        }]
    }
    result = _openai_chat_to_ollama(openai_resp, "m")
    assert result["message"]["thinking"] == "step by step"
    assert result["message"]["content"] == "answer"


# --- _stream_openai_chat thinking ---

def test_stream_openai_chat_thinking_chunks() -> None:
    lines = [
        f"data: {json.dumps({'choices': [{'delta': {'reasoning_content': 'hmm'}}]})}",
        f"data: {json.dumps({'choices': [{'delta': {'content': 'hello'}}]})}",
        "data: [DONE]",
    ]
    response = _FakeOpenAIResponse(lines)
    chunks = asyncio.run(_collect_async(_stream_openai_chat(response, "m")))
    decoded = [json.loads(c) for c in chunks]

    assert decoded[0]["message"]["thinking"] == "hmm"
    assert decoded[0]["done"] is False
    assert decoded[1]["message"]["content"] == "hello"
    assert decoded[2]["done"] is True


# --- _stream_openai_chat tool_calls ---

def test_stream_openai_chat_tool_calls_accumulated() -> None:
    lines = [
        f"data: {json.dumps({'choices': [{'delta': {'tool_calls': [{'index': 0, 'id': 'c1', 'type': 'function', 'function': {'name': 'fn', 'arguments': ''}}]}}]})}",
        f"data: {json.dumps({'choices': [{'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': '{\"k\":'}}]}}]})}",
        f"data: {json.dumps({'choices': [{'delta': {'tool_calls': [{'index': 0, 'function': {'arguments': '\"v\"}'}}]}}]})}",
        "data: [DONE]",
    ]
    response = _FakeOpenAIResponse(lines)
    chunks = asyncio.run(_collect_async(_stream_openai_chat(response, "m")))
    done_chunk = json.loads(chunks[-1])

    assert done_chunk["done"] is True
    tc = done_chunk["message"]["tool_calls"]
    assert tc[0]["function"]["name"] == "fn"
    assert tc[0]["function"]["arguments"] == {"k": "v"}
