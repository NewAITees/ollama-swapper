# CLI entry points for the proxy and model management commands.
# Usage examples:
#   ollama-swapper proxy --config /path/to/config.yaml
#   ollama-swapper ps | ollama-swapper sweep | ollama-swapper stop llama3:latest
from __future__ import annotations

import json
import sys
from pathlib import Path

import typer
import uvicorn

from .config import load_config
from .proxy import build_proxy_app, parse_listen
from .sweep import parse_ps_output, run_ps, stop_models

app = typer.Typer(help="Ollama swapper CLI")


@app.command("proxy")
def proxy_start(
    config: Path = typer.Option(..., "--config", "-c", exists=True),
) -> None:
    """Start the proxy server."""
    loaded_config = load_config(config)
    listen = parse_listen(loaded_config.server.listen)
    proxy_app = build_proxy_app(loaded_config)
    uvicorn.run(proxy_app, host=listen.host, port=listen.port)


@app.command("ps")
def ps_command() -> None:
    """Show models loaded in Ollama."""
    output = run_ps()
    typer.echo(output)


@app.command("sweep")
def sweep_command() -> None:
    """Stop all models currently loaded in Ollama."""
    output = run_ps()
    models = parse_ps_output(output)
    if not models:
        typer.echo("No models loaded.")
        raise typer.Exit(code=0)

    result = stop_models(models)
    typer.echo(json.dumps({"stopped": result.stopped, "failed": result.failed}, indent=2))
    if result.failed:
        raise typer.Exit(code=1)


@app.command("stop")
def stop_command(model: str) -> None:
    """Stop a single model."""
    result = stop_models([model])
    if result.failed:
        typer.echo(f"Failed to stop: {model}")
        raise typer.Exit(code=1)
    typer.echo(f"Stopped: {model}")


def main() -> None:
    app()


if __name__ == "__main__":
    sys.exit(main())
