# Repository Guidelines

## Project Structure & Module Organization
- `src/ollama_swapper/`: Core implementation (CLI, proxy, policy, config, sweep). Entry point is `cli.py`.
- `tests/`: Pytest suite (`test_*.py`) plus shared fixtures in `conftest.py`.
- `README.md`: Usage examples and configuration format (YAML/JSON).
- `pyproject.toml`: Project metadata, dependencies, pytest options.

## Build, Test, and Development Commands
- `pip install -e .`: Install in editable mode for local development.
- `ollama-swapper proxy --config /path/to/config.yaml`: Run the proxy locally.
- `ollama-swapper ps`: List loaded models via the proxy.
- `ollama-swapper sweep`: Stop all loaded models.
- `pytest`: Run the test suite (configured with `-q` in `pyproject.toml`).

## Coding Style & Naming Conventions
- Python 3.10+; follow PEP 8 with 4-space indentation.
- Modules and functions use `snake_case`; classes use `PascalCase`.
- Keep CLI flags and options consistent with existing commands in `cli.py`.
- No formatter/linter is configured in the repo; keep changes minimal and readable.

## Testing Guidelines
- Framework: `pytest`.
- Naming: files `test_*.py`, functions `test_*`.
- Add tests for policy parsing, config loading, and sweep behavior when touching those areas.

## Commit & Pull Request Guidelines
- Commit history is short and uses concise, imperative messages (e.g., “Add proxy CLI and policy enforcement”).
- PRs should include:
  - A brief summary of behavior changes.
  - Any config changes or new CLI flags.
  - Test evidence (command + result), or a short rationale if tests are not run.

## Configuration Notes
- Configuration supports YAML or JSON and follows the `server` / `policy` schema described in `README.md`.
- When adding config keys, update both `config.py` and the documentation.
