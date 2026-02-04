# FastAPI proxy that forwards requests to Ollama and injects policy defaults.
# Usage: build_proxy_app(config) then run via uvicorn (see cli.py).
from __future__ import annotations

import json
import logging
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


def build_proxy_app(config: AppConfig, verbose: bool = False) -> FastAPI:
    app = FastAPI()
    logger = logging.getLogger("ollama_swapper.proxy")
    if not logger.handlers:
        logging.basicConfig(level=logging.DEBUG if verbose else logging.INFO)

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
                body = json.dumps(payload).encode("utf-8")
                headers["content-length"] = str(len(body))
            elif payload is not None:
                logger.debug(
                    "skipping policy injection: non-dict payload type=%s path=%s",
                    type(payload).__name__,
                    path,
                )

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

        response_headers = dict(upstream_response.headers)
        return StreamingResponse(
            _stream_response(upstream_response),
            status_code=upstream_response.status_code,
            headers=response_headers,
            background=BackgroundTask(_close_upstream),
        )

    return app
