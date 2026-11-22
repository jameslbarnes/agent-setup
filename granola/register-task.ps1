# Registers or updates the "Granola Watch" scheduled task: watch.py every 5 minutes. It runs as
# your account without a stored password (S4U), so it works in the background with no window.
#   powershell -NoProfile -ExecutionPolicy Bypass -File register-task.ps1 [-Disable]
param([switch]$Disable)
$ErrorActionPreference = 'Stop'

$python = 'C:\Users\you\AppData\Local\Programs\Python\Python312\pythonw.exe'
$script = Join-Path $PSScriptRoot 'watch.py'
$action = New-ScheduledTaskAction -Execute $python -Argument "-I `"$script`""
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10) `
    -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType S4U -RunLevel Limited
$description = 'Starts a Paseo session for each new Granola meeting (what it was about, follow-ups). ' +
    "Code: $PSScriptRoot. State: %LOCALAPPDATA%\agent-setup\granola-watch."

Register-ScheduledTask -TaskName 'Granola Watch' -Action $action -Trigger $trigger -Settings $settings `
    -Principal $principal -Description $description -Force | Out-Null
if ($Disable) { Disable-ScheduledTask -TaskName 'Granola Watch' | Out-Null }
Get-ScheduledTask -TaskName 'Granola Watch' | Select-Object TaskName, State
