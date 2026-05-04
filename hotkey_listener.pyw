import ctypes
import ctypes.wintypes
import json
import logging
import subprocess
import sys
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "video_uploader_config.json"
LOG_PATH = APP_DIR / "hotkey.log"
CHILD_LOG_PATH = APP_DIR / "hotkey_child.log"
UPLOADER_PATH = APP_DIR / "video_uploader.py"

MODIFIERS = {
    "ALT": 0x0001,
    "CTRL": 0x0002,
    "CONTROL": 0x0002,
    "SHIFT": 0x0004,
    "WIN": 0x0008,
    "WINDOWS": 0x0008,
}

VK_KEYS = {
    "F1": 0x70,
    "F2": 0x71,
    "F3": 0x72,
    "F4": 0x73,
    "F5": 0x74,
    "F6": 0x75,
    "F7": 0x76,
    "F8": 0x77,
    "F9": 0x78,
    "F10": 0x79,
    "F11": 0x7A,
    "F12": 0x7B,
    "SPACE": 0x20,
    "TAB": 0x09,
}


logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("discord_video_hotkey")


def load_hotkey():
    if not CONFIG_PATH.exists():
        return "ALT+U"
    with CONFIG_PATH.open("r", encoding="utf-8") as config_file:
        config = json.load(config_file)
    return config.get("hotkey", "ALT+U")


def parse_hotkey(hotkey):
    parts = [part.strip().upper() for part in hotkey.replace("-", "+").split("+") if part.strip()]
    if len(parts) < 2:
        raise ValueError("Hotkey must include at least one modifier and one key, for example ALT+U.")

    modifiers = 0
    key_name = parts[-1]
    for modifier in parts[:-1]:
        if modifier not in MODIFIERS:
            raise ValueError(f"Unsupported hotkey modifier: {modifier}")
        modifiers |= MODIFIERS[modifier]

    if key_name in VK_KEYS:
        key_code = VK_KEYS[key_name]
    elif len(key_name) == 1:
        key_code = ord(key_name)
    else:
        raise ValueError(f"Unsupported hotkey key: {key_name}")

    return modifiers, key_code


def creation_flags():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def uploader_python():
    candidates = [
        APP_DIR / "venv" / "Scripts" / "python.exe",
        APP_DIR / ".venv" / "Scripts" / "python.exe",
        Path(sys.executable),
    ]
    for candidate in candidates:
        if candidate.exists() and can_run_uploader_imports(candidate):
            return str(candidate)
        logger.info("Skipping unusable Python candidate: %s", candidate)
    return sys.executable


def can_run_uploader_imports(candidate):
    try:
        result = subprocess.run(
            [str(candidate), "-c", "import discord, ffmpeg"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creation_flags(),
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


def launch_uploader(active_process):
    if active_process and active_process.poll() is None:
        logger.info("Upload already running; ignoring hotkey press.")
        return active_process

    python_path = uploader_python()
    logger.info("Launching uploader with %s", python_path)
    child_log = CHILD_LOG_PATH.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            [python_path, str(UPLOADER_PATH)],
            cwd=str(APP_DIR),
            stdout=child_log,
            stderr=child_log,
            creationflags=creation_flags(),
        )
        child_log.close()
        return process
    except Exception:
        child_log.close()
        raise


def main():
    hotkey = load_hotkey()
    modifiers, key_code = parse_hotkey(hotkey)
    hotkey_id = 1
    user32 = ctypes.windll.user32

    if not user32.RegisterHotKey(None, hotkey_id, modifiers, key_code):
        raise OSError(f"Could not register hotkey: {hotkey}")

    logger.info("Registered hotkey: %s", hotkey)
    message = ctypes.wintypes.MSG()
    active_process = None

    try:
        while user32.GetMessageW(ctypes.byref(message), None, 0, 0) != 0:
            if message.message == 0x0312 and message.wParam == hotkey_id:
                active_process = launch_uploader(active_process)
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
    finally:
        user32.UnregisterHotKey(None, hotkey_id)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        logger.exception("Hotkey listener stopped.")
