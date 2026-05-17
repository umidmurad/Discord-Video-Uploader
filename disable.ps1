$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "Discord Video Uploader Hotkey"

function Test-IsAdmin {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = [Security.Principal.WindowsPrincipal]::new($identity)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

Write-Host "Stopping Discord Video Uploader listener processes..."
Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like "*hotkey_listener.pyw*" -and $_.CommandLine -like "*$appDir*" } |
    ForEach-Object {
        Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host "Stopped listener process $($_.ProcessId)."
    }

Write-Host "Removing startup task if it exists..."
$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
    if (-not (Test-IsAdmin)) {
        Write-Warning "The listener was stopped, but removing the startup task requires an Administrator PowerShell."
        Write-Warning "Re-run this command from an Administrator PowerShell:"
        Write-Warning "powershell -ExecutionPolicy Bypass -File .\disable.ps1"
        exit 1
    }

    try {
        Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
        Write-Host "Removed scheduled task: $taskName"
    } catch {
        Write-Warning "Could not remove scheduled task: $($_.Exception.Message)"
        Write-Warning "Run PowerShell as Administrator and try again."
        exit 1
    }
} else {
    Write-Host "Scheduled task not found: $taskName"
}

Write-Host "Disabled Discord Video Uploader hotkey. Config and logs were kept."
