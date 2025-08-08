import os
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class BrowserConfig:
    port: int = int(os.getenv("CHROME_CDP_PORT", "9222"))
    user_data_dir: str = os.getenv("USER_DATA_DIR", "./chrome_data")
    headless: bool = os.getenv("HEADLESS_MODE", "false").lower() == "true"


def start() -> None:
    """
    Start Chrome with the remote debugging port enabled.
    Minimal stub to mirror claude-web's browser launcher.
    """
    cfg = BrowserConfig()
    chrome_cmd = os.getenv("CHROME_BIN", "google-chrome")

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
