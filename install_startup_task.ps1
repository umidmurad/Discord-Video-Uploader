$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$listenerPath = Join-Path $appDir "hotkey_listener.pyw"
$taskName = "Discord Video Uploader Hotkey"

$pythonw = (Get-Command pythonw.exe -ErrorAction SilentlyContinue).Source
if (-not $pythonw) {
    $pyw = (Get-Command pyw.exe -ErrorAction SilentlyContinue).Source
    if (-not $pyw) {
        throw "Could not find pythonw.exe or pyw.exe. Install Python and enable the py launcher or add Python to PATH."
    }
    $pythonw = $pyw
}

$action = New-ScheduledTaskAction -Execute $pythonw -Argument "`"$listenerPath`"" -WorkingDirectory $appDir
$trigger = New-ScheduledTaskTrigger -AtLogOn
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DisallowStartIfOnBatteries:$false -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description "Starts the silent Discord video uploader hotkey listener at login." -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host "Installed and started scheduled task: $taskName"
