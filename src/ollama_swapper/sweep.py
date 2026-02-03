from __future__ import annotations

import subprocess
from dataclasses import dataclass
from typing import Iterable


@dataclass
class SweepResult:
    stopped: list[str]
    failed: list[str]


def parse_ps_output(output: str) -> list[str]:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return []

    models: list[str] = []
    for line in lines[1:]:
        parts = line.split()
        if parts:
            models.append(parts[0])
    return models


def run_ps() -> str:
    completed = subprocess.run(
        ["ollama", "ps"],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "ollama ps failed")
    return completed.stdout


def stop_models(models: Iterable[str]) -> SweepResult:
    stopped: list[str] = []
    failed: list[str] = []
    for model in models:
        completed = subprocess.run(
            ["ollama", "stop", model],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode == 0:
            stopped.append(model)
        else:
            failed.append(model)
    return SweepResult(stopped=stopped, failed=failed)
