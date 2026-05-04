$ErrorActionPreference = "Stop"

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$taskName = "Discord Video Uploader Hotkey"
$localFiles = @(
    "video_uploader_config.json",
    "bot.log",
    "hotkey.log",
    "hotkey_child.log",
    "uploader.lock"
)

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
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
    Write-Host "Removed scheduled task: $taskName"
} else {
    Write-Host "Scheduled task not found: $taskName"
}

Write-Host "Deleting project-local config, logs, and lock files..."
foreach ($fileName in $localFiles) {
    $path = Join-Path $appDir $fileName
    if (Test-Path -LiteralPath $path) {
        Remove-Item -LiteralPath $path -Force
        Write-Host "Deleted $fileName"
    }
}

Write-Host "Uninstall cleanup complete. Project files and Game Bar captures were left untouched."
