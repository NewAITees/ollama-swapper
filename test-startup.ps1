# Test script for start-ollama.ps1

Write-Host "=== Pre-check ==="
$procs = Get-Process | Where-Object { $_.Name -like '*ollama*' }
if ($procs) {
    foreach ($p in $procs) { Write-Host "Still running: $($p.Name) PID $($p.Id)" }
} else {
    Write-Host "No ollama processes running. Clean state."
}

Write-Host "`n=== Running start-ollama.ps1 ==="
& "C:\analysis2\ollama-swapper\start-ollama.ps1"

Write-Host "`n=== Post-check: Processes ==="
Start-Sleep -Seconds 3
$procs = Get-Process | Where-Object { $_.Name -like '*ollama*' }
foreach ($p in $procs) {
    Write-Host "  $($p.Name) PID $($p.Id)"
}

Write-Host "`n=== Port check ==="
netstat -ano | Select-String ":1143[46] " | ForEach-Object { Write-Host "  $_" }

Write-Host "`n=== Health check: ollama serve on 11436 ==="
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11436" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Status: $($r.StatusCode) - $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))"
} catch {
    Write-Host "  FAILED: $_"
}

Write-Host "`n=== Health check: swapper on 11434 ==="
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434" -UseBasicParsing -TimeoutSec 5
    Write-Host "  Status: $($r.StatusCode) - $($r.Content.Substring(0, [Math]::Min(100, $r.Content.Length)))"
} catch {
    Write-Host "  FAILED: $_"
}

Write-Host "`n=== Test: ollama list via swapper ==="
try {
    $r = Invoke-WebRequest -Uri "http://127.0.0.1:11434/api/tags" -UseBasicParsing -TimeoutSec 10
    Write-Host "  Status: $($r.StatusCode)"
    $models = ($r.Content | ConvertFrom-Json).models
    Write-Host "  Models found: $($models.Count)"
    foreach ($m in $models | Select-Object -First 3) { Write-Host "    - $($m.name)" }
    if ($models.Count -gt 3) { Write-Host "    ... and $($models.Count - 3) more" }
} catch {
    Write-Host "  FAILED: $_"
}

Write-Host "`n=== DONE ==="
