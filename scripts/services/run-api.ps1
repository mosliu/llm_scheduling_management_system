param(
    [string]$BindHost = "0.0.0.0",
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$PythonExe = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Set-Location $RepoRoot
& $PythonExe -m uvicorn apps.api.main:app --host $BindHost --port $Port
