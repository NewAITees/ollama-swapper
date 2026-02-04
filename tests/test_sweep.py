# Tests for parsing `ollama ps` output into model names.
# Usage: pytest tests/test_sweep.py
from ollama_swapper.sweep import parse_ps_output


def test_parse_ps_output() -> None:
    sample = """
NAME            ID              SIZE   PROCESSOR   UNTIL
llama3:latest   abc123          4.7GB  GPU         2 minutes from now
qwen2:latest    def456          7.4GB  GPU         1 minute from now
""".strip()

    models = parse_ps_output(sample)

    assert models == ["llama3:latest", "qwen2:latest"]
