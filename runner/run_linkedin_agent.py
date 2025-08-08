import argparse
import os
import sys
import time
from pathlib import Path

# Ensure repo root is on sys.path when running as a script
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.linkedin_agent import LinkedInAgent  # noqa: E402
from config import load_env, CDPConfig  # noqa: E402
from vendor.claude_web.browser import start as start_browser  # noqa: E402
import requests  # type: ignore  # noqa: E402


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--location", default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"))
    parser.add_argument("--limit", type=int, default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")))
    parser.add_argument("--approve-outreach", dest="approve_outreach", action="store_true")
    args = parser.parse_args()

    # Ensure Chrome is running with CDP on the configured port; propagate to env for all components
    cdp = CDPConfig()
    os.environ["CHROME_CDP_PORT"] = str(cdp.port)
    # Attach if DevTools is already up; otherwise launch a new Chrome instance
    def _cdp_alive() -> bool:
        try:
            r = requests.get(f"http://localhost:{cdp.port}/json", timeout=0.5)
            return bool(r.ok)
        except Exception:
            return False

    if _cdp_alive():
        print(f"Attaching to existing Chrome on port {cdp.port}")
    else:
        print("Starting Chrome with CDP on port", cdp.port)
        start_browser()
        # Wait for DevTools endpoint to be ready
        for _ in range(50):
            if _cdp_alive():
                break
            time.sleep(0.2)

    agent = LinkedInAgent()
    prompt = (
        f"Open LinkedIn, search for people with '{args.query}' in {args.location}. "
        f"Collect up to {args.limit} candidates. For each, open the profile and call extract_profile. "
        f"Keep actions small and verify URL/location changes."
    )

    res = agent.call(query=prompt)
    print("Run complete. Steps:")
    steps = getattr(res, "step_history", getattr(res, "steps", []))
    for i, s in enumerate(steps, 1):
        print(i, getattr(s, 'thought', getattr(s, 'action', 'step')))
        if getattr(s, 'tool_name', None):
            print("  ->", s.tool_name, getattr(s, 'tool_args', {}), "=>", (str(getattr(s, 'tool_result', None))[:120] if getattr(s, 'tool_result', None) is not None else None))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
