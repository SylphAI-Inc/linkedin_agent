import argparse
import os
import time
from agents.linkedin_agent import build_agent
from config import load_env


def main():
    load_env()
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", required=True)
    parser.add_argument("--location", default=os.getenv("DEFAULT_LOCATION", "San Francisco Bay Area"))
    parser.add_argument("--limit", type=int, default=int(os.getenv("DEFAULT_SEARCH_LIMIT", "10")))
    parser.add_argument("--approve-outreach", dest="approve_outreach", action="store_true")
    args = parser.parse_args()

    # Ensure Chrome is running with CDP
    print("Ensure Chrome is started with CDP on port", os.getenv("CHROME_CDP_PORT", "9222"))

    agent, runner = build_agent()

    prompt = (
        f"Open LinkedIn, search for people with '{args.query}' in {args.location}. "
        f"Collect up to {args.limit} candidates. For each, open the profile and call extract_profile. "
        f"Keep actions small and verify URL/location changes."
    )

    res = runner.call(agent=agent, query=prompt, context={"approve_outreach": args.approve_outreach})
    print("Run complete. Steps:")
    for i, s in enumerate(res.steps, 1):
        print(i, s.thought)
        if s.tool_name:
            print("  ->", s.tool_name, s.tool_args, "=>", (str(s.tool_result)[:120] if s.tool_result is not None else None))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
