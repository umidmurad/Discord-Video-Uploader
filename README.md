# Discord Video Uploader

Uploads the newest Xbox Game Bar capture from your Captures folder to a Discord channel.

## How It Works

Daily use is:

1. Save a Game Bar clip with `Win + Alt + G`.
2. Wait for the clip to finish saving.
3. Press the configured upload hotkey, default `Alt + U`.
4. The newest original capture is trimmed/compressed/uploaded.
5. Temporary trim/compressed files are deleted after a successful upload.

The moving parts are:

- `video_uploader.py`: performs one upload cycle, then exits.
- `hotkey_listener.pyw`: waits quietly in the background for the hotkey.
- `enable.ps1`: installs and starts the Windows startup task.
- `disable.ps1`: stops the hotkey listener and removes the startup task.
- `uninstall.ps1`: disables the hotkey and deletes private local config/log files.

`Task Scheduler -> hotkey_listener.pyw -> video_uploader.py`

Keep the project files together. If you move the whole project folder after enabling startup, run `enable.ps1` again from the new folder because Task Scheduler stores the exact path.

## Requirements

- Python 3.12+
- FFmpeg installed and available on `PATH`
- Python packages:

```powershell
pip install discord.py ffmpeg-python
```

## Configure

Create the private config:

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

## Test Once

Run one upload directly:

```powershell
python video_uploader.py
```

This tests your token, channel ID, FFmpeg install, package install, and capture folder without involving the hotkey listener.

## Enable

Run PowerShell as Administrator from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\enable.ps1
```

This creates and starts a Task Scheduler task named `Discord Video Uploader Hotkey`. The task starts `hotkey_listener.pyw` at Windows login.

## Disable

Run PowerShell as Administrator from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\disable.ps1
```

This stops this project's hotkey listener and removes the startup task. It keeps `video_uploader_config.json` and `uploader.log`.

## Uninstall

Run PowerShell as Administrator from this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\uninstall.ps1
```

The uninstall script:

- stops this project's `hotkey_listener.pyw` process
- removes the `Discord Video Uploader Hotkey` startup task
- deletes project-local private config, log, and lock files

It does not delete the project folder, your original Xbox Game Bar recordings in `Videos\Captures`, Python, FFmpeg, or the Discord bot application from Discord's Developer Portal.

## Discord Setup

1. Open the [Discord Developer Portal](https://discord.com/developers/applications).
2. Create an application and add a bot.
3. Copy the bot token.
4. Invite the bot to your server with:
   - `Send Messages`
   - `Attach Files`
   - `Read Messages/View Channels`
5. Enable Discord Developer Mode, then copy the destination channel ID.

## Game Bar Notes

Xbox Game Bar's default "record that" shortcut is `Win + Alt + G`, which saves the last 30 seconds to `Videos\Captures`. This project does not try to control Game Bar directly. Instead, it trims the newest capture afterward, which is more reliable and keeps the upload workflow independent from the game.

## Troubleshooting

### Check The Only Log

Everything writes to one file:

```powershell
Get-Content -Tail 120 .\uploader.log
```

Older versions used `bot.log`, `hotkey.log`, and `hotkey_child.log`. New runs use only `uploader.log`.

### Hotkey Listener Looks Like Nothing Happened

This is normal. `pythonw` and `pyw` run without a console window.

Check whether the listener registered:

```powershell
Get-Content -Tail 40 .\uploader.log
```

Look for:

```text
Registered hotkey: ALT+U
```

### Could Not Register Hotkey

If `uploader.log` says:

```text
Could not register hotkey: ALT+U
```

another process is already using that hotkey. Most commonly, an older listener is still running.

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\disable.ps1
powershell -ExecutionPolicy Bypass -File .\enable.ps1
```

### Hotkey Says It Launched But No Upload Happens

Check:

```powershell
Get-Content -Tail 120 .\uploader.log
```

Common causes:

- the virtual environment does not have `discord.py` or `ffmpeg-python`
- FFmpeg is not on `PATH`
- `video_uploader_config.json` is missing the bot token or channel ID
- the newest capture is still being written
- the configured capture folder is wrong

### Startup Task Stops Working After Moving Folder

Run `enable.ps1` again from the new folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\enable.ps1
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
