#!/usr/bin/env python3
"""
Log Viewer for LinkedIn Agent
Quick tool to view the latest log files
"""

from pathlib import Path
import argparse


def get_latest_log_files(log_dir="logs"):
    """Get the latest log files from the logs directory"""
    log_path = Path(log_dir)
    if not log_path.exists():
        print(f"❌ Log directory '{log_dir}' does not exist")
        return None

    # Find the latest timestamp pattern
    log_files = list(log_path.glob("*_*.log"))
    if not log_files:
        print(f"❌ No log files found in '{log_dir}'")
        return None

    # Group by timestamp (assuming format: type_YYYYMMDD_HHMMSS.log)
    timestamps = set()
    for log_file in log_files:
        parts = log_file.stem.split("_")
        if len(parts) >= 3:
            timestamp = f"{parts[-2]}_{parts[-1]}"
            timestamps.add(timestamp)

    if not timestamps:
        print("❌ No valid log files found")
        return None

    latest_timestamp = max(timestamps)

    # Find all log files with the latest timestamp
    latest_files = {}
    for log_file in log_files:
        if latest_timestamp in log_file.name:
            log_type = log_file.name.replace(f"_{latest_timestamp}.log", "")
            latest_files[log_type] = log_file

    return latest_files, latest_timestamp


def view_log(log_file, lines=50):
    """View the contents of a log file"""
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            content = f.readlines()

        print(f"\n{'=' * 60}")
        print(f"📄 {log_file.name}")
        print(f"{'=' * 60}")

        if lines and len(content) > lines:
            print(f"... (showing last {lines} lines of {len(content)} total)")
            content = content[-lines:]

        for line in content:
            print(line.rstrip())

    except Exception as e:
        print(f"❌ Error reading {log_file}: {e}")


def main():
    parser = argparse.ArgumentParser(description="View LinkedIn Agent log files")
    parser.add_argument(
        "--type",
        choices=["workflow", "debug", "agent_steps", "errors", "all"],
        default="workflow",
        help="Type of log to view",
    )
    parser.add_argument(
        "--lines", type=int, default=50, help="Number of lines to show (0 for all)"
    )
    parser.add_argument(
        "--latest", action="store_true", help="Show only the latest session logs"
    )

    args = parser.parse_args()

    # Get latest log files
    result = get_latest_log_files()
    if not result:
        return

    latest_files, timestamp = result

    print(f"🕒 Latest log session: {timestamp}")
    print(f"📁 Available logs: {', '.join(latest_files.keys())}")

    if args.type == "all":
        # Show all log types
        for log_type in ["workflow", "debug", "agent_steps", "errors"]:
            if log_type in latest_files:
                view_log(latest_files[log_type], args.lines)
    else:
        # Show specific log type
        if args.type in latest_files:
            view_log(latest_files[args.type], args.lines)
        else:
            print(f"❌ Log type '{args.type}' not found")
            print(f"💡 Available: {', '.join(latest_files.keys())}")


if __name__ == "__main__":
    main()
