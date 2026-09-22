param(
    [string]$TaskName = 'TR-Databento-OrderFlow-Daily',
    [string]$At = '03:30',
    [string]$DataRoot = 'C:\Users\roeea\sagiv-repos\traders-engine\market-data\databento-orderflow-daily'
)
$ErrorActionPreference = 'Stop'
$runner = Join-Path $PSScriptRoot 'run_orderflow_daily.ps1'
$arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$runner`" -DataRoot `"$DataRoot`""
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arguments
$when = [datetime]::Today.Add([timespan]::Parse($At))
$trigger = New-ScheduledTaskTrigger -Daily -At $when
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 8) -MultipleInstances IgnoreNew
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Get-ScheduledTask -TaskName $TaskName | Select-Object TaskName, State
