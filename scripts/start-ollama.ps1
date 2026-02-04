$ErrorActionPreference = "Stop"

$env:OLLAMA_HOST = "http://127.0.0.1:11436"

$ollamaApp = "C:\Users\perso\AppData\Local\Programs\Ollama\ollama app.exe"
if (-not (Test-Path $ollamaApp)) {
  Write-Error "Ollama app.exe not found at $ollamaApp"
}

Start-Process -FilePath $ollamaApp
