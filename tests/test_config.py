from pathlib import Path

from ollama_swapper.config import load_config


def test_load_config_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        """
server:
  listen: "127.0.0.1:11434"
  upstream: "http://127.0.0.1:11436"
policy:
  defaults:
    num_ctx: 8192
    keep_alive: 0
  models:
    "llama3.1:8b-instruct-q4_K_M":
      num_ctx: 32768
      keep_alive: "60s"
""".strip()
    )

    config = load_config(config_path)

    assert config.server.listen == "127.0.0.1:11434"
    assert config.policy.defaults.num_ctx == 8192
    assert config.policy.models["llama3.1:8b-instruct-q4_K_M"].keep_alive == "60s"
