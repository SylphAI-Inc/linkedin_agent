import os
import shutil
import subprocess
import sys
from dataclasses import dataclass

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


@dataclass
class BrowserConfig:
    port: int = int(os.getenv("CHROME_CDP_PORT", "9222"))
    user_data_dir: str = os.getenv("USER_DATA_DIR", "./chrome_data")
    headless: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"


def _which_chrome() -> str:
    # Respect explicit env if set
    env_bin = os.getenv("CHROME_BIN")
    if env_bin:
        return env_bin
    # Try common names/paths
    candidates = [
        "google-chrome",
        "google-chrome-stable",
        "chromium-browser",
        "chromium",
        "/usr/bin/chromium-browser",
        "/snap/bin/chromium",
    ]
    for c in candidates:
        path = shutil.which(c) or (c if os.path.exists(c) else None)
        if path:
            return path
    raise FileNotFoundError(
        "Chrome/Chromium not found. Set CHROME_BIN to your browser path (e.g., /usr/bin/chromium-browser)."
    )


def start() -> None:
    """
    Start Chrome with the remote debugging port enabled.
    Minimal stub to mirror claude-web's browser launcher.
    """
    cfg = BrowserConfig()
    chrome_cmd = _which_chrome()

    args = [
        chrome_cmd,
        f"--remote-debugging-port={cfg.port}",
        f"--user-data-dir={cfg.user_data_dir}",
    ]
    if cfg.headless:
        args += [
            "--headless=new",
            "--disable-gpu",
            "--no-sandbox",
            "--disable-dev-shm-usage",
        ]

    print("Launching Chrome:", " ".join(args))
    subprocess.Popen(args)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "start"
    if cmd == "start":
        start()
    else:
        print("Unknown command", cmd)
