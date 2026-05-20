param(
    [string]$TaskPrefix = "LSMS",
    [string]$ApiHost = "0.0.0.0",
    [int]$ApiPort = 8000,
    [double]$WorkerPollIntervalSeconds = 2.0,
    [int]$WorkerLimit = 10,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..\\..")).Path
$PowerShellExe = (Get-Command powershell.exe).Source
$ApiScript = Join-Path $RepoRoot "scripts\\services\\run-api.ps1"
$WorkerScript = Join-Path $RepoRoot "scripts\\services\\run-worker.ps1"
$ApiTaskName = "$TaskPrefix-API"
$WorkerTaskName = "$TaskPrefix-Worker"

$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -MultipleInstances IgnoreNew `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1)

$apiArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$ApiScript`" -BindHost `"$ApiHost`" -Port $ApiPort"
$workerArgs = "-NoProfile -ExecutionPolicy Bypass -File `"$WorkerScript`" -PollIntervalSeconds $WorkerPollIntervalSeconds -Limit $WorkerLimit"

$apiAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $apiArgs
$workerAction = New-ScheduledTaskAction -Execute $PowerShellExe -Argument $workerArgs

foreach ($taskName in @($ApiTaskName, $WorkerTaskName)) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        if (-not $Force) {
            throw "Scheduled task already exists: $taskName. Re-run with -Force to replace it."
        }
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    }
}

Register-ScheduledTask `
    -TaskName $ApiTaskName `
    -Action $apiAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "LLM Scheduling Management System API" `
    -User "SYSTEM" `
    -RunLevel Highest | Out-Null

Register-ScheduledTask `
    -TaskName $WorkerTaskName `
    -Action $workerAction `
    -Trigger $trigger `
    -Settings $settings `
    -Description "LLM Scheduling Management System Worker" `
    -User "SYSTEM" `
    -RunLevel Highest | Out-Null

Write-Output "Installed scheduled tasks:"
Write-Output "  $ApiTaskName"
Write-Output "  $WorkerTaskName"
