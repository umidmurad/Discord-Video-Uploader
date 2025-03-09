# Video Uploader Discord Bot

This script uploads the most recent video from a specified folder to a Discord channel. It also compresses videos larger than 10MB before uploading.

## Prerequisites

### 1. Create a Discord Bot
1. Go to the [Discord Developer Portal](https://discord.com/developers/applications).
2. Click **New Application**, name your bot, and go to the **Bot** section.
3. Click **Add Bot** and copy the **Token** (you will need this later).
4. Under **Privileged Gateway Intents**, enable **Message Content Intent**.
5. Click **Save Changes**.

### 2. Get Your Discord Channel ID
1. Enable **Developer Mode** in Discord (User Settings > Advanced > Developer Mode).
2. Right-click the channel where videos should be uploaded and select **Copy ID**.
3. Save this ID for later use.

### 3. Give the Bot Required Permissions
When adding the bot to a server, ensure it has the following permissions:
- `Send Messages`
- `Attach Files`
- `Read Messages`

To generate an invite link with the necessary permissions:
1. Go to the **OAuth2** section in the Developer Portal.
2. Under **OAuth2 URL Generator**, select `bot` and `applications.commands`.
3. In the **Bot Permissions** section, select `Send Messages`, `Attach Files`, and `Read Messages`.
4. Copy and open the generated link to add the bot to your server.

## Installation

### 1. Install Dependencies
Ensure you have Python 3.12+ installed, then install the required packages:
```bash
pip install discord ffmpeg
```
You also need to install **FFmpeg**:
- Windows: Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add it to your system path.
- Linux/macOS: Install via package manager (`sudo apt install ffmpeg` or `brew install ffmpeg`).

### 2. Configure the Script
Edit the script to include your bot token and channel ID:
```python
DISCORD_BOT_TOKEN = "YOUR_BOT_TOKEN"
DISCORD_CHANNEL_ID = YOUR_CHANNEL_ID
VIDEO_DIRECTORY = r"C:\\Users\\YOUR_USERNAME\\Videos\\Captures"  # Adjust to your folder
```

### 3. Run the Bot
```bash
python video_uploader.py
```

## Running the Script with AutoHotkey

To easily run the script using a keyboard shortcut:

1. **Install AutoHotkey** from [https://www.autohotkey.com/](https://www.autohotkey.com/).
2. **Create an AutoHotkey script (`run_video_uploader.ahk`)**:
   - Right-click inside a folder → `New` → `AutoHotkey Script`.
   - Open the file in Notepad and add:
     ```ahk
     ^!U:: ; Press Ctrl + Alt + U to run the script
     Run, pythonw "C:\path\to\video_uploader.py"
     return
     ```
     *(Replace `C:\path\to\video_uploader.py` with the actual script path.)*
3. **Run the AutoHotkey script** by double-clicking it.
4. Press `Ctrl + Alt + U` to start the bot.

---

## Notes
- The bot only runs once per execution and uploads the latest video.
- Large videos are automatically compressed to 10MB.
- The bot will shut down after uploading a video.

## Troubleshooting
- **Bot not responding?** Ensure the bot token is correct and the bot is in the server.
- **Video not uploading?** Check file size and ensure it’s in the correct directory.
- **FFmpeg errors?** Make sure FFmpeg is installed and added to the system path.

---
🚀 Enjoy automated video uploads to Discord!

