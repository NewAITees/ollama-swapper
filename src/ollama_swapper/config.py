# Config loader and data structures for server/policy settings.
# Usage: load_config("/path/to/config.yaml") or load_config("/path/to/config.json")
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

import yaml


@dataclass
class ServerConfig:
    listen: str
    upstream: str


@dataclass
class PolicyDefaults:
    num_ctx: int | None = None
    keep_alive: int | str | None = None


@dataclass
class ModelPolicy:
    num_ctx: int | None = None
    keep_alive: int | str | None = None
    upstream: str | None = None


@dataclass
class PolicyConfig:
    defaults: PolicyDefaults = field(default_factory=PolicyDefaults)
    models: dict[str, ModelPolicy] = field(default_factory=dict)


@dataclass
class AppConfig:
    server: ServerConfig
    policy: PolicyConfig


def _load_raw_config(path: Path) -> Mapping[str, Any]:
    if path.suffix.lower() in {".yaml", ".yml"}:
        with path.open("r", encoding="utf-8") as handle:
            return yaml.safe_load(handle) or {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _parse_policy_defaults(raw: Mapping[str, Any]) -> PolicyDefaults:
    return PolicyDefaults(
        num_ctx=raw.get("num_ctx"),
        keep_alive=raw.get("keep_alive"),
    )


def _parse_model_policy(raw: Mapping[str, Any]) -> ModelPolicy:
    return ModelPolicy(
        num_ctx=raw.get("num_ctx"),
        keep_alive=raw.get("keep_alive"),
        upstream=raw.get("upstream"),
    )


def load_config(path: str | Path) -> AppConfig:
    config_path = Path(path)
    raw = _load_raw_config(config_path)
    if "server" not in raw or "policy" not in raw:
        raise ValueError("config must include server and policy sections")

    server_raw = raw["server"]
    policy_raw = raw["policy"]
    defaults_raw = policy_raw.get("defaults", {})
    models_raw = policy_raw.get("models", {})

    server = ServerConfig(
        listen=server_raw["listen"],
        upstream=server_raw["upstream"],
    )
    policy = PolicyConfig(
        defaults=_parse_policy_defaults(defaults_raw),
        models={
            name: _parse_model_policy(model_raw)
            for name, model_raw in models_raw.items()
        },
    )
    return AppConfig(server=server, policy=policy)
