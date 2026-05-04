# Discord Video Uploader

Uploads the newest Xbox Game Bar capture from your Captures folder to a Discord channel.

The current flow is:

1. Press the configured hotkey.
2. The newest capture is found.
3. If configured, the clip is trimmed to the last 15 seconds.
4. If it is still larger than the Discord limit, it is compressed.
5. The processed clip is uploaded through your Discord bot.

## How It Works

The project has three main runtime files:

- `video_uploader.py`: performs one upload cycle, then exits.
- `hotkey_listener.pyw`: runs silently in the background and launches `video_uploader.py` when the configured hotkey is pressed.
- `install_startup_task.ps1`: creates a Windows Task Scheduler task so `hotkey_listener.pyw` starts when you log into Windows.

Normal daily flow:

1. Save a Game Bar clip with `Win + Alt + G`.
2. Wait for the clip to finish saving.
3. Press the configured upload hotkey, default `Alt + U`.
4. The uploader trims/compresses/uploads the newest original capture.
5. Temporary trim/compressed files are deleted after a successful upload.

`hotkey_listener.pyw` finds `video_uploader.py` in the same folder as itself. Keep the project files together.

If you move the whole project folder after installing the startup task, run `install_startup_task.ps1` again from the new folder. Task Scheduler stores the exact folder path from the time it was installed.

## Requirements

- Python 3.12+
- FFmpeg installed and available on `PATH`
- Python packages:

```powershell
pip install discord.py ffmpeg-python
```

## Discord Setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application and add a bot.
3. Copy the bot token.
4. Invite the bot to your server with:
   - `Send Messages`
   - `Attach Files`
   - `Read Messages/View Channels`
5. Enable Discord Developer Mode, then copy the destination channel ID.

## Configure

Run once to create your private config:

```powershell
python video_uploader.py --init-config
```

If `python` is not on PATH, copy `video_uploader_config.example.json` to `video_uploader_config.json` manually.

Edit `video_uploader_config.json`:

```json
{
  "video_directory": "%USERPROFILE%\\Videos\\Captures",
  "discord_bot_token": "YOUR_BOT_TOKEN",
  "discord_channel_id": 0,
  "max_upload_mb": 10,
  "trim_last_seconds": 15,
  "trim_mode": "copy",
  "hotkey": "ALT+U",
  "delete_processed_files": true,
  "message": "New video uploaded:"
}
```

`trim_mode` can be:

- `copy`: fastest and avoids re-encoding during the trim. The start point may snap to the nearest keyframe.
- `encode`: more exact 15 second trims, but slower and re-encodes before the size check.

When `delete_processed_files` is `true`, generated trim/compressed files are deleted after a successful upload. The original Game Bar recording is kept.

## Run Once

```powershell
python video_uploader.py
```

This is useful for testing your token, channel ID, FFmpeg install, and capture folder.

## Silent Hotkey

`hotkey_listener.pyw` replaces AutoHotkey. It registers the configured global hotkey, then runs `video_uploader.py` silently when pressed.

Start it manually:

```powershell
pythonw hotkey_listener.pyw
```

If your Python install uses the Windows launcher:

```powershell
pyw hotkey_listener.pyw
```

`pythonw` and `pyw` do not print anything to PowerShell. If the listener started correctly, PowerShell will simply return to the prompt. Check `hotkey.log` for `Registered hotkey`.

## Start At Login

Run PowerShell from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup_task.ps1
```

This creates and starts a Task Scheduler task named `Discord Video Uploader Hotkey`. It launches `hotkey_listener.pyw` at login without a console window.

## Uninstall

Run PowerShell from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

The uninstall script:

- stops this project's `hotkey_listener.pyw` process
- removes the `Discord Video Uploader Hotkey` startup task
- deletes project-local private config, logs, and lock files

It does not delete the project folder, your original Xbox Game Bar recordings in `Videos\Captures`, Python, FFmpeg, or the Discord bot application from Discord's Developer Portal.

Manual fallback:

```powershell
Stop-Process -Name pythonw -Force -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "Discord Video Uploader Hotkey" -Confirm:$false
Remove-Item .\video_uploader_config.json, .\bot.log, .\hotkey.log, .\hotkey_child.log, .\uploader.lock -Force -ErrorAction SilentlyContinue
```

## Game Bar Notes

Xbox Game Bar's default "record that" shortcut is `Win + Alt + G`, which saves the last 30 seconds to `Videos\Captures`. This project does not try to control Game Bar directly. Instead, it trims the newest capture afterward, which is more reliable and keeps the upload workflow independent from the game.

## Troubleshooting

### Hotkey Listener Looks Like Nothing Happened

This is normal when using `pythonw` or `pyw`. They run without a console window.

Check whether the listener registered:

```powershell
Get-Content -Tail 40 .\hotkey.log
```

Look for:

```text
Registered hotkey: ALT+U
```

### Could Not Register Hotkey

If `hotkey.log` says:

```text
Could not register hotkey: ALT+U
```

another process is already using that hotkey. Most commonly, an older listener is still running.

Stop this project's listener:

```powershell
Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe'" |
  Where-Object { $_.CommandLine -like "*hotkey_listener.pyw*" } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

Then start the listener again.

### Hotkey Says It Launched But No Upload Happens

Check the logs:

```powershell
Get-Content -Tail 80 .\hotkey.log
Get-Content -Tail 80 .\hotkey_child.log
Get-Content -Tail 80 .\bot.log
```

Common causes:

- the virtual environment does not have `discord.py` or `ffmpeg-python`
- FFmpeg is not on `PATH`
- `video_uploader_config.json` is missing the bot token or channel ID
- the newest capture is still being written
- the configured capture folder is wrong

### Startup Task Stops Working After Moving Folder

Run the installer again from the new folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_startup_task.ps1
```

The task will be overwritten with the new path.

### Test Without The Hotkey

Run the uploader directly:

```powershell
python video_uploader.py
```

If direct upload works but the hotkey does not, the issue is in `hotkey_listener.pyw`, the venv path, or the startup task.

### Check Required Packages

From the activated virtual environment:

```powershell
python -c "import discord, ffmpeg; print('packages ok')"
```

Check FFmpeg:

```powershell
ffmpeg -version
```

## Logs

- `bot.log`: upload, trim, compression, and Discord errors
- `hotkey.log`: hotkey listener startup and launch errors
- `hotkey_child.log`: uploader errors from hotkey-launched runs
