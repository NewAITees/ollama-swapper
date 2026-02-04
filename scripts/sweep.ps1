$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$venvScript = Join-Path $projectRoot ".venv\Scripts\Activate.ps1"
if (-not (Test-Path $venvScript)) {
  Write-Error "venv not found at $venvScript"
}

. $venvScript

$env:OLLAMA_HOST = "http://127.0.0.1:11436"

ollama-swapper sweep
