param(
    [string]$TaskPrefix = "LSMS"
)

$ErrorActionPreference = "Stop"
$taskNames = @("$TaskPrefix-API", "$TaskPrefix-Worker")
$rows = foreach ($taskName in $taskNames) {
    $task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
    if (-not $task) {
        [PSCustomObject]@{
            TaskName = $taskName
            Exists = $false
            State = "missing"
            LastRunTime = $null
            LastTaskResult = $null
        }
        continue
    }
    $info = Get-ScheduledTaskInfo -TaskName $taskName
    [PSCustomObject]@{
        TaskName = $taskName
        Exists = $true
        State = $task.State
        LastRunTime = $info.LastRunTime
        LastTaskResult = $info.LastTaskResult
    }
}

$rows | Format-Table -AutoSize
