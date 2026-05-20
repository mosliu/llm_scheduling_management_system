param(
    [string]$TaskPrefix = "LSMS"
)

$ErrorActionPreference = "Stop"

foreach ($taskName in @("$TaskPrefix-API", "$TaskPrefix-Worker")) {
    Start-ScheduledTask -TaskName $taskName
    Write-Output "Started $taskName"
}
