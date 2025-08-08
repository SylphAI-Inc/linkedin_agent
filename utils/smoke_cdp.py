import os
import sys
import time
from pathlib import Path

# Ensure repo root on path for local script execution
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from vendor.claude_web.browser import start as start_browser  # noqa: E402
from vendor.claude_web.tools.web_tool import WebTool  # noqa: E402
from config import CDPConfig  # noqa: E402


def main():
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    print("Starting Chrome on", cdp.port)
    start_browser()
    time.sleep(1.0)
    w = WebTool(port=cdp.port)
    print("Connecting WS...")
    w.connect()
    print("Connected. Navigating...")
    w.go("https://www.example.com")
    title = w.js("document.title")
    print("Title:", title)
    w.close()


if __name__ == "__main__":
    main()
