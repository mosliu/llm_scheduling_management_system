param(
    [double]$PollIntervalSeconds = 2.0,
    [int]$Limit = 10
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$PythonExe = Join-Path $RepoRoot ".venv\\Scripts\\python.exe"

if (-not (Test-Path $PythonExe)) {
    throw "Python executable not found: $PythonExe"
}

Set-Location $RepoRoot
& $PythonExe scripts/run_worker_service.py --mode loop --poll-interval $PollIntervalSeconds --limit $Limit
