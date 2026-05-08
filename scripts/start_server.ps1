$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$python = Join-Path $root '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
    throw "Expected virtual environment interpreter at $python"
}

Set-Location $root
& $python -m uvicorn mordecai.main:app --host 127.0.0.1 --port 8000 --reload
