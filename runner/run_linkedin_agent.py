import argparse
import os
import time
from agents.linkedin_agent import LinkedInAgent
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

    agent = LinkedInAgent()
    prompt = (
        f"Open LinkedIn, search for people with '{args.query}' in {args.location}. "
        f"Collect up to {args.limit} candidates. For each, open the profile and call extract_profile. "
        f"Keep actions small and verify URL/location changes."
    )

    res = agent.call(query=prompt, context={"approve_outreach": args.approve_outreach})
    print("Run complete. Steps:")
    for i, s in enumerate(res.steps, 1):
        print(i, getattr(s, 'thought', getattr(s, 'action', 'step')))
        if getattr(s, 'tool_name', None):
            print("  ->", s.tool_name, getattr(s, 'tool_args', {}), "=>", (str(getattr(s, 'tool_result', None))[:120] if getattr(s, 'tool_result', None) is not None else None))
        time.sleep(0.1)


if __name__ == "__main__":
    main()
