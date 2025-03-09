import os
import re
import sys
import time
import asyncio
import discord
import ffmpeg
import subprocess

# Discord bot setup
intents = discord.Intents.default()
client = discord.Client(intents=intents)
VIDEO_DIRECTORY  = r"C:\Users\YOUR_USERNAME\Videos\Captures"  # Change this to your actual path
DISCORD_BOT_TOKEN = "MY_BOT_TOKEN"  # Replace with your bot token
DISCORD_CHANNEL_ID = MY_CHANNEL_ID  # Replace with your channel ID



def get_latest_video(directory):
    """Finds the most recently modified video file in the given directory."""
    video_extensions = (".mp4", ".mov", ".avi", ".mkv")
    videos = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if f.lower().endswith(video_extensions)
    ]
    if not videos:
        return None
    return max(videos, key=os.path.getmtime)  # Get the most recently modified file


def compress_video(video_full_path, output_file_name, target_size_kb):
    """Compresses the video to the target size."""
    try:
        min_audio_bitrate = 32000
        max_audio_bitrate = 256000

        # Get video metadata
        probe = ffmpeg.probe(video_full_path)
        duration = float(probe['format']['duration'])
        audio_bitrate = float(
            next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)['bit_rate'])

        # Calculate target bitrate
        target_total_bitrate = (target_size_kb * 1024 * 8) / (1.073741824 * duration)

        # Adjust audio bitrate if necessary
        if 10 * audio_bitrate > target_total_bitrate:
            audio_bitrate = max(min_audio_bitrate, min(target_total_bitrate / 10, max_audio_bitrate))

        # Compute video bitrate
        video_bitrate = target_total_bitrate - audio_bitrate

        # Run compression
        cmd = [
            'ffmpeg', '-i', video_full_path,
            '-c:v', 'libx264',
            '-b:v', str(video_bitrate),
            '-pass', '1',
            '-f', 'mp4',
            'NUL' if sys.platform == "win32" else '/dev/null'
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        cmd = [
            'ffmpeg', '-i', video_full_path,
            '-c:v', 'libx264',
            '-b:v', str(video_bitrate),
            '-pass', '2',
            '-c:a', 'aac',
            '-b:a', str(audio_bitrate),
            output_file_name
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        print(f"✅ Video compressed successfully: {output_file_name}")
        return output_file_name

    except Exception as e:
        print(f"❌ Error during compression: {str(e)}")
        return None


async def upload_to_discord(file_path):
    """Uploads the given video file to Discord."""
    await client.wait_until_ready()  # Ensure bot is connected
    channel = client.get_channel(DISCORD_CHANNEL_ID)

    if not channel:
        print("❌ Error: Could not find Discord channel.")
        return

    if not os.path.exists(file_path):
        print(f"❌ Error: File not found: {file_path}")
        return

    # Check if file is empty
    if os.path.getsize(file_path) == 0:
        print(f"❌ Error: File is empty: {file_path}")
        return

    # Ensure the file is not being modified
    last_modified_time = os.path.getmtime(file_path)
    time.sleep(5)
    if last_modified_time != os.path.getmtime(file_path):
        print(f"❌ File is still being written: {file_path}")
        return

    # Rename file to remove special characters
    base_name = os.path.basename(file_path)
    sanitized_name = re.sub(r'[^\w\s.-]', '', base_name)
    sanitized_path = os.path.join(os.path.dirname(file_path), sanitized_name)

    if sanitized_name != base_name:
        os.rename(file_path, sanitized_path)
        file_path = sanitized_path

    # Compress if larger than 10MB
    if os.path.getsize(file_path) > 10 * 1024 * 1024:
        print(f"⚠️ File too large, compressing: {file_path}")
        output_file_path = os.path.join(os.path.dirname(file_path), "compressed_" + os.path.basename(file_path))
        compressed_video = compress_video(file_path, output_file_path, target_size_kb=10000)  # 10MB
        if compressed_video and os.path.exists(compressed_video):
            file_path = compressed_video
        else:
            print("❌ Compression failed, skipping upload.")
            return

    try:
        with open(file_path, "rb") as file:
            discord_file = discord.File(file, filename=os.path.basename(file_path))
            await channel.send(content=f"🎥 New video uploaded: `{os.path.basename(file_path)}`", file=discord_file)
        print(f"✅ Uploaded successfully: {file_path}")
    except Exception as e:
        print(f"❌ Failed to upload {file_path}: {e}")
        await channel.send(f"❌ Failed to upload `{os.path.basename(file_path)}`.")


@client.event
async def on_ready():
    print(f"✅ Logged in as {client.user}")

    latest_video = get_latest_video(VIDEO_DIRECTORY)
    if latest_video:
        print(f"📂 Found latest video: {latest_video}")
        await upload_to_discord(latest_video)
    else:
        print("❌ No video found in directory.")

    await client.close()  # Stop bot after execution


# Run the bot
client.run(DISCORD_BOT_TOKEN)
