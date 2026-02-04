# FastAPI proxy that forwards requests to Ollama and injects policy defaults.
# Usage: build_proxy_app(config) then run via uvicorn (see cli.py).
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncIterator
from urllib.parse import urljoin

import httpx
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from .config import AppConfig
from .policy import apply_policy


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


def build_proxy_app(config: AppConfig) -> FastAPI:
    app = FastAPI()

    @app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
    async def proxy(path: str, request: Request) -> Response:
        upstream_url = urljoin(config.server.upstream.rstrip("/") + "/", path)
        body = await request.body()
        headers = dict(request.headers)
        method = request.method

        if path in {"api/chat", "api/generate"} and body:
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                payload = apply_policy(payload, config.policy)
                body = json.dumps(payload).encode("utf-8")
                headers["content-length"] = str(len(body))

        client = httpx.AsyncClient(timeout=None)
        upstream_request = client.build_request(
            method,
            upstream_url,
            content=body,
            headers=headers,
            params=request.query_params,
        )
        upstream_response = await client.send(upstream_request, stream=True)

        async def _close_upstream() -> None:
            await upstream_response.aclose()
            await client.aclose()

        response_headers = dict(upstream_response.headers)
        return StreamingResponse(
            _stream_response(upstream_response),
            status_code=upstream_response.status_code,
            headers=response_headers,
            background=BackgroundTask(_close_upstream),
        )

    return app
