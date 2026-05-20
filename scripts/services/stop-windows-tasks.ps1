param(
    [string]$TaskPrefix = "LSMS"
)

$ErrorActionPreference = "Stop"

foreach ($taskName in @("$TaskPrefix-API", "$TaskPrefix-Worker")) {
    Stop-ScheduledTask -TaskName $taskName
    Write-Output "Stopped $taskName"
}
