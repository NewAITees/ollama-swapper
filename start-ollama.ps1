# Ollama serve + ollama-swapper startup script
# Starts ollama.exe serve first, waits for it to be ready, then starts ollama-swapper proxy.

$ollamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$swapperExe = "C:\analysis2\ollama-swapper\.venv\Scripts\ollama-swapper.exe"
$swapperConfig = "C:\analysis2\ollama-swapper\config.yaml"
$ollamaHost = "127.0.0.1:11436"

# Start ollama serve in background
$env:OLLAMA_HOST = $ollamaHost
Start-Process -FilePath $ollamaExe -ArgumentList "serve" -WindowStyle Hidden

# Wait for ollama to be ready (up to 60 seconds)
$maxWait = 60
$waited = 0
Write-Host "Waiting for Ollama server on $ollamaHost ..."
while ($waited -lt $maxWait) {
    try {
        $response = Invoke-WebRequest -Uri "http://$ollamaHost" -UseBasicParsing -TimeoutSec 2 -ErrorAction Stop
        if ($response.StatusCode -eq 200) {
            Write-Host "Ollama server is ready. (${waited}s)"
            break
        }
    } catch {
        # not ready yet
    }
    Start-Sleep -Seconds 1
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Host "WARNING: Ollama server did not become ready within ${maxWait}s. Starting swapper anyway."
}

# Start ollama-swapper proxy
Start-Process -FilePath $swapperExe -ArgumentList "proxy --config $swapperConfig" -WindowStyle Hidden
Write-Host "ollama-swapper started."
