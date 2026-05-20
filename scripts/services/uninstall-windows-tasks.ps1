param(
    [string]$TaskPrefix = "LSMS"
)

$ErrorActionPreference = "Stop"

foreach ($taskName in @("$TaskPrefix-API", "$TaskPrefix-Worker")) {
    $existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if ($existing) {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Output "Removed $taskName"
    } else {
        Write-Output "Not found: $taskName"
    }
}
