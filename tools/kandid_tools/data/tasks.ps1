# Kandid scheduled tasks, under the Task Scheduler folder \Kandid\. Called by kandid_tools.scheduler with
# validated parameters only (fixed task names, HH:MM times, absolute paths); no value is ever evaluated as code.
param(
    [Parameter(Mandatory = $true)][ValidateSet('register', 'unregister', 'list')][string]$Action,
    [ValidatePattern('^[a-z]+$')][string]$Name,
    [ValidatePattern('^([01]\d|2[0-3]):[0-5]\d$')][string]$At,
    [string]$Execute,
    [string]$Arguments,
    [string]$WorkingDirectory
)

$ErrorActionPreference = 'Stop'
$folder = '\Kandid\'

switch ($Action) {
    'register' {
        $taskAction = New-ScheduledTaskAction -Execute $Execute -Argument $Arguments -WorkingDirectory $WorkingDirectory
        $trigger = New-ScheduledTaskTrigger -Daily -At $At
        # Runs later if the computer was off at the set time; a stuck run is stopped after 30 minutes.
        $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
        Register-ScheduledTask -TaskPath $folder -TaskName $Name -Action $taskAction -Trigger $trigger `
            -Settings $settings -Description 'Kandid: prepare only, never sends.' -Force | Out-Null
    }
    'unregister' {
        Get-ScheduledTask -TaskPath $folder -ErrorAction SilentlyContinue |
            Where-Object { -not $Name -or $_.TaskName -eq $Name } |
            Unregister-ScheduledTask -Confirm:$false
    }
    'list' {
        $tasks = @(Get-ScheduledTask -TaskPath $folder -ErrorAction SilentlyContinue | ForEach-Object {
                $info = Get-ScheduledTaskInfo -InputObject $_
                [pscustomobject]@{
                    name    = $_.TaskName
                    state   = [string]$_.State
                    next    = if ($info.NextRunTime) { $info.NextRunTime.ToString('s') } else { $null }
                    last    = if ($info.LastRunTime -and $info.LastRunTime.Year -gt 2000) { $info.LastRunTime.ToString('s') } else { $null }
                }
            })
        ConvertTo-Json -InputObject $tasks -Compress
    }
}
