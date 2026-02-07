$port = 8001
$ollamaPort = 11434

# --- CHECK OLLAMA ---
Write-Host "Checking Ollama (port $ollamaPort)..."
$ollamaConnections = Get-NetTCPConnection -LocalPort $ollamaPort -ErrorAction SilentlyContinue

if (-not $ollamaConnections) {
    Write-Host "Ollama is not running. Starting Ollama..."
    Start-Process -FilePath "ollama" -ArgumentList "serve" -NoNewWindow
    Write-Host "Waiting for Ollama to initialize..."
    Start-Sleep -Seconds 5
} else {
    Write-Host "Ollama is running."
}

# --- START BACKEND ---
Write-Host "Checking backend port $port..."

$connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue

if ($connections) {
    $pids = $connections | Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($p in $pids) {
        if ($p -ne 0) {
            Write-Host "Killing process $p on port $port"
            Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "Port $port is free"
}

Start-Sleep -Seconds 1
Write-Host "Starting backend..."
python backend/main.py
