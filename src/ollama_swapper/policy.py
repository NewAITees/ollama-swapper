# Policy resolution and injection for Ollama request payloads.
# Usage: apply_policy(payload_dict, policy_config)
from __future__ import annotations

from typing import Any, Mapping

from .config import AppConfig, PolicyConfig


def _resolve_policy(model: str | None, policy: PolicyConfig) -> Mapping[str, Any]:
    resolved = {
        "num_ctx": policy.defaults.num_ctx,
        "keep_alive": policy.defaults.keep_alive,
    }
    if model and model in policy.models:
        model_policy = policy.models[model]
        if model_policy.num_ctx is not None:
            resolved["num_ctx"] = model_policy.num_ctx
        if model_policy.keep_alive is not None:
            resolved["keep_alive"] = model_policy.keep_alive
    return resolved


def resolve_upstream(model: str | None, config: AppConfig) -> str:
    if model and model in config.policy.models:
        model_policy = config.policy.models[model]
        if model_policy.upstream:
            return model_policy.upstream
    return config.server.upstream


def apply_policy(payload: dict[str, Any], policy: PolicyConfig) -> dict[str, Any]:
    model = payload.get("model")
    resolved = _resolve_policy(model, policy)

    options = payload.get("options")
    if options is None:
        options = {}
        payload["options"] = options

    if "num_ctx" not in options and resolved.get("num_ctx") is not None:
        options["num_ctx"] = resolved["num_ctx"]

    if payload.get("keep_alive") is None and resolved.get("keep_alive") is not None:
        payload["keep_alive"] = resolved["keep_alive"]

    return payload
