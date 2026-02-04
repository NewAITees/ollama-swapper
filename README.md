# ollama-swapper
A lightweight proxy + CLI to enforce Ollama model policies (context length + keep-alive) and sweep idle models.

## Goals
- Apply model-specific `num_ctx` defaults when clients do **not** specify them.
- Default to `keep_alive=0` to unload models immediately after generation.
- Provide a sweep command to stop any models that remain loaded.

## Install
```bash
pip install -e .
```

## Configuration
YAML or JSON is supported. Example:
```yaml
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
    "qwen2.5-coder:32b-instruct-q4_K_M":
      num_ctx: 65536
      keep_alive: 0
```

## Usage
### Start proxy
```bash
ollama-swapper proxy --config /path/to/config.yaml
```

### Start proxy (verbose policy logging)
```bash
ollama-swapper proxy --config /path/to/config.yaml --verbose
```

### Show loaded models
```bash
ollama-swapper ps
```

### Sweep (stop-all)
```bash
ollama-swapper sweep
```

### Stop a single model
```bash
ollama-swapper stop llama3:latest
```

## Operational notes
- Recommended ports: run the proxy on `11434` and Ollama itself on `11436`.
- The proxy only injects `options.num_ctx` and `keep_alive` when the client omits them.
- If you bypass the proxy, use `ollama-swapper sweep` to reclaim VRAM.
- CLI commands (`ps`, `sweep`, `stop`) require `ollama` to be on PATH.
- If `ollama-swapper` is not on PATH, run it via
  `C:\analysis2\ollama-swapper\.venv\Scripts\ollama-swapper.exe`.

## Change Ollama default port
You can change Ollama's listen host/port with the `OLLAMA_HOST` environment variable.

Example (PowerShell):
```powershell
$env:OLLAMA_HOST="127.0.0.1:11436"
ollama serve
```

After changing this, set `server.upstream` in `config.yaml` to the same address.

## Startup setup (Windows)
### Goal
- Start Ollama automatically on port `11436`
- Start `ollama-swapper` automatically on login

### Steps
1) **Write the user environment variable**
```powershell
setx OLLAMA_HOST "http://0.0.0.0:11436"
```

2) **Restart (or sign out / sign in)**
Environment variables apply to new logon sessions.

3) **Ensure Ollama auto-starts**
Assumes there is an `Ollama` shortcut in Startup.

4) **Auto-start ollama-swapper**
Create a Startup shortcut with:
- Target:
  `C:\analysis2\ollama-swapper\.venv\Scripts\ollama-swapper.exe`
- Arguments:
  `proxy --config C:\analysis2\ollama-swapper\config.yaml`
- Working directory:
  `C:\analysis2\ollama-swapper`

### Verify
```powershell
Invoke-WebRequest -Uri http://127.0.0.1:11436/ -Method GET
```
