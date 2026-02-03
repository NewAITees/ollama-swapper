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
