# FastAPI proxy that forwards requests to Ollama and injects policy defaults.
# Usage: build_proxy_app(config) then run via uvicorn (see cli.py).
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from .config import AppConfig
from .policy import apply_policy, resolve_upstream


@dataclass(frozen=True)
class ListenAddress:
    host: str
    port: int


def parse_listen(listen: str) -> ListenAddress:
    if ":" not in listen:
        raise ValueError("listen must be in host:port format")
    host, port_str = listen.rsplit(":", 1)
    return ListenAddress(host=host, port=int(port_str))


async def _stream_response(response: httpx.Response) -> AsyncIterator[bytes]:
    async for chunk in response.aiter_bytes():
        yield chunk


def _json_bytes(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload).encode("utf-8")


def _ollama_chat_to_openai(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": payload.get("model"),
        "messages": payload.get("messages", []),
        "stream": payload.get("stream", False),
        "max_tokens": -1,
    }


def _ollama_generate_to_openai(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "model": payload.get("model"),
        "prompt": payload.get("prompt", ""),
        "stream": payload.get("stream", False),
        "max_tokens": -1,
    }


def _openai_chat_to_ollama(payload: dict[str, Any], model: str | None) -> dict[str, Any]:
    content = ""
    for choice in payload.get("choices", []):
        message = choice.get("message") or {}
        if message.get("content") is not None:
            content = message.get("content") or ""
            break
    return {
        "model": model,
        "message": {"role": "assistant", "content": content},
        "done": True,
    }


def _openai_generate_to_ollama(payload: dict[str, Any], model: str | None) -> dict[str, Any]:
    content = ""
    for choice in payload.get("choices", []):
        if choice.get("text") is not None:
            content = choice.get("text") or ""
            break
    return {
        "model": model,
        "response": content,
        "done": True,
    }


async def _stream_openai_chat(response: httpx.Response, model: str | None) -> AsyncIterator[bytes]:
    async for line in response.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data:
            continue
        if data == "[DONE]":
            yield _json_bytes({"model": model, "done": True}) + b"\n"
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices", []):
            delta = choice.get("delta") or {}
            content = delta.get("content")
            if content is None:
                continue
            yield _json_bytes(
                {
                    "model": model,
                    "message": {"role": "assistant", "content": content},
                    "done": False,
                }
            ) + b"\n"


async def _stream_openai_generate(
    response: httpx.Response, model: str | None
) -> AsyncIterator[bytes]:
    async for line in response.aiter_lines():
        if not line or not line.startswith("data:"):
            continue
        data = line[5:].strip()
        if not data:
            continue
        if data == "[DONE]":
            yield _json_bytes({"model": model, "done": True}) + b"\n"
            break
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        for choice in payload.get("choices", []):
            text = choice.get("text")
            if text is None:
                continue
            yield _json_bytes(
                {
                    "model": model,
                    "response": text,
                    "done": False,
                }
            ) + b"\n"


def build_proxy_app(config: AppConfig, verbose: bool = False) -> FastAPI:
    app = FastAPI()
    logger = logging.getLogger("ollama_swapper.proxy")
    if not logger.handlers:
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def proxy(path: str, request: Request) -> Response:
        body = await request.body()
        headers = dict(request.headers)
        method = request.method
        payload: dict[str, Any] | None = None
        model: str | None = None

        if path in {"api/chat", "api/generate"} and body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                logger.debug("skipping policy injection: invalid json body path=%s", path)
                payload = None
            if isinstance(payload, dict):
                before_options = dict(payload.get("options") or {})
                before_keep_alive = payload.get("keep_alive")
                payload = apply_policy(payload, config.policy)
                after_options = dict(payload.get("options") or {})
                after_keep_alive = payload.get("keep_alive")
                logger.debug(
                    "policy applied model=%s options_before=%s options_after=%s keep_alive_before=%s keep_alive_after=%s",
                    payload.get("model"),
                    before_options,
                    after_options,
                    before_keep_alive,
                    after_keep_alive,
                )
                model = payload.get("model")
                body = json.dumps(payload).encode("utf-8")
                headers["content-length"] = str(len(body))
            elif payload is not None:
                logger.debug(
                    "skipping policy injection: non-dict payload type=%s path=%s",
                    type(payload).__name__,
                    path,
                )

        upstream_base = resolve_upstream(model, config)
        use_openai = (
            upstream_base != config.server.upstream
            and path in {"api/chat", "api/generate"}
            and isinstance(payload, dict)
        )
        if use_openai:
            if path == "api/chat":
                upstream_path = "v1/chat/completions"
                openai_payload = _ollama_chat_to_openai(payload)
                stream = bool(openai_payload.get("stream"))
                stream_adapter = _stream_openai_chat
                response_adapter = _openai_chat_to_ollama
            else:
                upstream_path = "v1/completions"
                openai_payload = _ollama_generate_to_openai(payload)
                stream = bool(openai_payload.get("stream"))
                stream_adapter = _stream_openai_generate
                response_adapter = _openai_generate_to_ollama

            upstream_url = urljoin(upstream_base.rstrip("/") + "/", upstream_path)
            body = _json_bytes(openai_payload)
            headers["content-type"] = "application/json"
            headers["content-length"] = str(len(body))
        else:
            upstream_url = urljoin(upstream_base.rstrip("/") + "/", path)

        client = httpx.AsyncClient(timeout=None)
        upstream_request = client.build_request(
            method,
            upstream_url,
            content=body,
            headers=headers,
            params=request.query_params,
        )
        try:
            upstream_response = await client.send(upstream_request, stream=True)
        except httpx.RequestError as exc:
            await client.aclose()
            logger.error(
                "upstream request failed method=%s url=%s error=%s",
                method,
                upstream_url,
                exc,
            )
            return Response("Upstream request failed", status_code=502)

        async def _close_upstream() -> None:
            await upstream_response.aclose()
            await client.aclose()

        if upstream_response.status_code >= 400 or not use_openai:
            response_headers = dict(upstream_response.headers)
            return StreamingResponse(
                _stream_response(upstream_response),
                status_code=upstream_response.status_code,
                headers=response_headers,
                background=BackgroundTask(_close_upstream),
            )

        if stream:
            return StreamingResponse(
                stream_adapter(upstream_response, model),
                status_code=upstream_response.status_code,
                headers={"content-type": "application/x-ndjson"},
                background=BackgroundTask(_close_upstream),
            )

        raw = await upstream_response.aread()
        await _close_upstream()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return Response(raw, status_code=upstream_response.status_code)
        converted = response_adapter(parsed, model)
        return Response(
            _json_bytes(converted),
            status_code=upstream_response.status_code,
            media_type="application/json",
        )

    return app
