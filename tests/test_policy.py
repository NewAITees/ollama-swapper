# Tests for policy resolution and payload mutation.
# Usage: pytest tests/test_policy.py
from ollama_swapper.config import AppConfig, PolicyConfig, PolicyDefaults, ModelPolicy, ServerConfig
from ollama_swapper.policy import apply_policy, resolve_upstream


def test_apply_policy_injects_defaults() -> None:
    policy = PolicyConfig(
        defaults=PolicyDefaults(num_ctx=8192, keep_alive=0),
        models={
            "llama3": ModelPolicy(num_ctx=32768, keep_alive="60s"),
        },
    )

    payload = {"model": "llama3", "messages": []}
    updated = apply_policy(payload, policy)

    assert updated["options"]["num_ctx"] == 32768
    assert updated["keep_alive"] == "60s"


def test_apply_policy_respects_client_options() -> None:
    policy = PolicyConfig(
        defaults=PolicyDefaults(num_ctx=8192, keep_alive=0),
        models={},
    )

    payload = {
        "model": "unknown",
        "messages": [],
        "options": {"num_ctx": 1234},
        "keep_alive": "10s",
    }
    updated = apply_policy(payload, policy)

    assert updated["options"]["num_ctx"] == 1234
    assert updated["keep_alive"] == "10s"


def test_resolve_upstream_uses_model_override() -> None:
    config = AppConfig(
        server=ServerConfig(listen="127.0.0.1:11434", upstream="http://127.0.0.1:11436"),
        policy=PolicyConfig(
            defaults=PolicyDefaults(),
            models={
                "nemotron-jp": ModelPolicy(upstream="http://127.0.0.1:18765"),
            },
        ),
    )

    assert resolve_upstream("nemotron-jp", config) == "http://127.0.0.1:18765"
    assert resolve_upstream("other", config) == "http://127.0.0.1:11436"
