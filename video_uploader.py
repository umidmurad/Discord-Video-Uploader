import argparse
import asyncio
import contextlib
import json
import logging
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import discord
import ffmpeg


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "video_uploader_config.json"
LOG_PATH = APP_DIR / "bot.log"
LOCK_PATH = APP_DIR / "uploader.lock"
VIDEO_EXTENSIONS = (".mp4", ".mov", ".avi", ".mkv")
GENERATED_PREFIXES = ("compressed_", "last_")

DEFAULT_CONFIG = {
    "video_directory": str(Path.home() / "Videos" / "Captures"),
    "discord_bot_token": "YOUR_BOT_TOKEN",
    "discord_channel_id": 0,
    "max_upload_mb": 10,
    "trim_last_seconds": 15,
    "trim_mode": "copy",
    "hotkey": "ALT+U",
    "delete_processed_files": True,
    "message": "New video uploaded:",
}


logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("discord_video_uploader")


def load_config(config_path=CONFIG_PATH):
    if not config_path.exists():
        config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        raise FileNotFoundError(
            f"Created {config_path}. Fill in your Discord token/channel settings, then run again."
        )

    with config_path.open("r", encoding="utf-8") as config_file:
        config = DEFAULT_CONFIG | json.load(config_file)

    config["video_directory"] = os.path.expandvars(os.path.expanduser(config["video_directory"]))
    config["discord_channel_id"] = int(config["discord_channel_id"])
    config["max_upload_bytes"] = int(float(config["max_upload_mb"]) * 1024 * 1024)
    return config


def validate_config(config):
    missing = []
    if not config["discord_bot_token"] or config["discord_bot_token"] == "YOUR_BOT_TOKEN":
        missing.append("discord_bot_token")
    if not config["discord_channel_id"]:
        missing.append("discord_channel_id")
    if missing:
        raise ValueError(f"Update these settings in {CONFIG_PATH}: {', '.join(missing)}")
    if not os.path.isdir(config["video_directory"]):
        raise FileNotFoundError(f"Video directory does not exist: {config['video_directory']}")


def get_latest_video(directory):
    logger.info("Searching for the latest video in %s", directory)
    videos = [
        os.path.join(directory, filename)
        for filename in os.listdir(directory)
        if is_source_video(filename)
    ]
    if not videos:
        logger.info("No videos found in the directory.")
        return None
    return max(videos, key=os.path.getmtime)


def is_source_video(filename):
    lower_filename = filename.lower()
    return lower_filename.endswith(VIDEO_EXTENSIONS) and not lower_filename.startswith(GENERATED_PREFIXES)


def wait_until_file_is_stable(file_path, checks=6, interval=1):
    previous_size = -1
    for _ in range(checks):
        current_size = os.path.getsize(file_path)
        if current_size > 0 and current_size == previous_size:
            return True
        previous_size = current_size
        time.sleep(interval)
    return False


def sanitize_filename(file_path):
    base_name = os.path.basename(file_path)
    sanitized_name = re.sub(r"[^\w\s.-]", "", base_name).strip()
    sanitized_name = sanitized_name or f"clip{Path(file_path).suffix}"
    sanitized_path = os.path.join(os.path.dirname(file_path), sanitized_name)

    if sanitized_name != base_name:
        os.rename(file_path, sanitized_path)
        logger.info("Renamed %s to %s", file_path, sanitized_path)
        return sanitized_path

    return file_path


def ffmpeg_creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def run_ffmpeg(cmd, cwd):
    logger.info("Running FFmpeg command: %s", " ".join(map(str, cmd)))
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=cwd,
        check=True,
        creationflags=ffmpeg_creation_flags(),
    )


def probe_video(video_path):
    return ffmpeg.probe(video_path)


def get_duration_seconds(video_path):
    probe = probe_video(video_path)
    return float(probe["format"]["duration"])


def get_audio_bitrate(probe):
    audio_stream = next((stream for stream in probe["streams"] if stream["codec_type"] == "audio"), None)
    if not audio_stream:
        return 0
    return int(audio_stream.get("bit_rate") or 128000)


def unique_output_path(source_path, prefix):
    source = Path(source_path)
    candidate = source.with_name(f"{prefix}{source.stem}{source.suffix}")
    counter = 2
    while candidate.exists():
        candidate = source.with_name(f"{prefix}{source.stem}_{counter}{source.suffix}")
        counter += 1
    return str(candidate)


def clean_ffmpeg_pass_logs(pass_log_prefix):
    for pass_log in Path(pass_log_prefix).parent.glob(f"{Path(pass_log_prefix).name}-*.log*"):
        with contextlib.suppress(OSError):
            pass_log.unlink()
            logger.info("Deleted FFmpeg pass log: %s", pass_log)


def clean_generated_files(generated_files):
    for generated_file in generated_files:
        if os.path.exists(generated_file):
            with contextlib.suppress(OSError):
                os.remove(generated_file)
                logger.info("Deleted generated file: %s", generated_file)


def trim_video(video_path, seconds, mode):
    seconds = float(seconds or 0)
    if seconds <= 0:
        return video_path

    duration = get_duration_seconds(video_path)
    if duration <= seconds + 0.5:
        logger.info("Skipping trim. Duration %.2fs is already within %.2fs.", duration, seconds)
        return video_path

    output_path = unique_output_path(video_path, f"last_{int(seconds)}s_")
    cwd = os.path.dirname(video_path)

    if mode == "encode":
        cmd = [
            "ffmpeg",
            "-y",
            "-sseof",
            f"-{seconds}",
            "-i",
            video_path,
            "-t",
            str(seconds),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "160k",
            "-movflags",
            "+faststart",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-sseof",
            f"-{seconds}",
            "-i",
            video_path,
            "-t",
            str(seconds),
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c",
            "copy",
            output_path,
        ]

    run_ffmpeg(cmd, cwd)
    if os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Trimmed file is empty: {output_path}")

    logger.info("Trimmed video saved to %s", output_path)
    return output_path


def compress_video(video_path, target_size_bytes):
    logger.info("Compressing video: %s", video_path)
    probe = probe_video(video_path)
    duration = float(probe["format"]["duration"])
    audio_bitrate = get_audio_bitrate(probe)

    min_audio_bitrate = 32000 if audio_bitrate else 0
    max_audio_bitrate = 160000 if audio_bitrate else 0
    target_total_bitrate = (target_size_bytes * 8) / (1.073741824 * duration)

    if audio_bitrate:
        if 10 * audio_bitrate > target_total_bitrate:
            audio_bitrate = max(min_audio_bitrate, min(target_total_bitrate / 10, max_audio_bitrate))
        else:
            audio_bitrate = min(audio_bitrate, max_audio_bitrate)

    video_bitrate = max(64000, target_total_bitrate - audio_bitrate)
    output_path = unique_output_path(video_path, "compressed_")
    cwd = os.path.dirname(video_path)
    null_output = "NUL" if sys.platform == "win32" else "/dev/null"

    pass_log_prefix = str(Path(output_path).with_suffix(""))
    first_pass = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-map",
        "0:v:0",
        "-c:v",
        "libx264",
        "-b:v",
        str(int(video_bitrate)),
        "-pass",
        "1",
        "-passlogfile",
        pass_log_prefix,
        "-an",
        "-f",
        "mp4",
        null_output,
    ]
    second_pass = [
        "ffmpeg",
        "-y",
        "-i",
        video_path,
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-b:v",
        str(int(video_bitrate)),
        "-pass",
        "2",
        "-passlogfile",
        pass_log_prefix,
        "-c:a",
        "aac",
        "-b:a",
        str(int(audio_bitrate or 96000)),
        "-movflags",
        "+faststart",
        output_path,
    ]

    try:
        run_ffmpeg(first_pass, cwd)
        run_ffmpeg(second_pass, cwd)
    finally:
        clean_ffmpeg_pass_logs(pass_log_prefix)

    if os.path.getsize(output_path) == 0:
        raise RuntimeError(f"Compressed file is empty: {output_path}")

    logger.info("Compressed video saved to %s", output_path)
    return output_path


async def upload_to_discord(file_path, config):
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)
    upload_result = {"uploaded": False}

    @client.event
    async def on_ready():
        try:
            logger.info("Logged in as %s", client.user)
            channel = client.get_channel(config["discord_channel_id"])
            if not channel:
                raise RuntimeError("Could not find Discord channel.")

            with open(file_path, "rb") as file:
                discord_file = discord.File(file, filename=os.path.basename(file_path))
                await channel.send(
                    content=f"{config['message']} `{os.path.basename(file_path)}`",
                    file=discord_file,
                )
            upload_result["uploaded"] = True
            logger.info("Uploaded successfully: %s", file_path)
        except Exception:
            logger.exception("Failed to upload %s", file_path)
        finally:
            await client.close()

    async with client:
        await client.start(config["discord_bot_token"])
    return upload_result["uploaded"]


async def process_latest_video(config):
    latest_video = get_latest_video(config["video_directory"])
    if not latest_video:
        logger.info("No video found in directory.")
        return False

    logger.info("Found latest video: %s", latest_video)
    if not wait_until_file_is_stable(latest_video):
        logger.info("File is still being written: %s", latest_video)
        return False

    original_video = latest_video
    working_video = sanitize_filename(latest_video)
    generated_files = []

    try:
        trimmed_video = trim_video(working_video, config["trim_last_seconds"], config["trim_mode"])
        if trimmed_video != working_video:
            generated_files.append(trimmed_video)
            working_video = trimmed_video

        target_size_bytes = int(config["max_upload_bytes"] * 0.95)
        if os.path.getsize(working_video) > config["max_upload_bytes"]:
            working_video = compress_video(working_video, target_size_bytes)
            generated_files.append(working_video)

        if os.path.getsize(working_video) > config["max_upload_bytes"]:
            raise RuntimeError(
                f"Processed file is still larger than {config['max_upload_mb']} MB: {working_video}"
            )

        uploaded = await upload_to_discord(working_video, config)
        if uploaded and config["delete_processed_files"]:
            clean_generated_files(generated_files)
        return uploaded
    except Exception:
        logger.exception("Processing failed for %s", original_video)
        return False


def parse_args():
    parser = argparse.ArgumentParser(description="Upload the latest Game Bar clip to Discord.")
    parser.add_argument("--init-config", action="store_true", help="Create the config file if it is missing.")
    return parser.parse_args()


@contextlib.contextmanager
def single_instance_lock():
    try:
        lock_fd = os.open(str(LOCK_PATH), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        if is_stale_lock(LOCK_PATH):
            logger.info("Removing stale lock file: %s", LOCK_PATH)
            with contextlib.suppress(OSError):
                LOCK_PATH.unlink()
            with single_instance_lock() as should_run:
                yield should_run
            return
        logger.info("Upload already running. Lock file exists: %s", LOCK_PATH)
        yield False
        return

    try:
        os.write(lock_fd, str(os.getpid()).encode("ascii"))
        yield True
    finally:
        os.close(lock_fd)
        with contextlib.suppress(OSError):
            LOCK_PATH.unlink()


def is_stale_lock(lock_path, max_age_seconds=30 * 60):
    try:
        return time.time() - lock_path.stat().st_mtime > max_age_seconds
    except OSError:
        return False


def main():
    args = parse_args()
    if args.init_config:
        if not CONFIG_PATH.exists():
            CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=2), encoding="utf-8")
        print(f"Config file: {CONFIG_PATH}")
        return 0

    try:
        config = load_config()
        validate_config(config)
        with single_instance_lock() as should_run:
            if not should_run:
                return 0
            uploaded = asyncio.run(process_latest_video(config))
        return 0 if uploaded else 1
    except Exception as exc:
        logger.exception("Uploader failed.")
        print(exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
