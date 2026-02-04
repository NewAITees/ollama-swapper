# Tests for proxy helpers.
# Usage: pytest tests/test_proxy.py
import pytest

from ollama_swapper.proxy import parse_listen


def test_parse_listen_parses_host_port() -> None:
    parsed = parse_listen("127.0.0.1:11434")
    assert parsed.host == "127.0.0.1"
    assert parsed.port == 11434


def test_parse_listen_requires_port() -> None:
    with pytest.raises(ValueError):
        parse_listen("127.0.0.1")
