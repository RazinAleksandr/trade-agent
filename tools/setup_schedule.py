#!/usr/bin/env python3
"""Install or remove the Polymarket trading cycle crontab entry.

Reads CYCLE_INTERVAL from .env (e.g., '4h', '30m', '1d') and installs
a crontab entry that runs run_cycle.sh on that schedule.

Usage:
    python tools/setup_schedule.py           # Install/update schedule
    python tools/setup_schedule.py --remove  # Remove schedule
    python tools/setup_schedule.py --show    # Show current crontab
"""

import argparse
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

CRON_MARKER = "# polymarket-trading-agent"


def interval_to_cron(interval: str) -> str:
    """Convert interval string (e.g. '4h', '30m', '1d') to cron expression.

    Supported formats:
        {N}m  -- every N minutes (1-59)
        {N}h  -- every N hours (1-23)
        1d    -- daily at midnight

    Args:
        interval: Human-friendly interval string.

    Returns:
        Cron expression string (e.g. '0 */4 * * *').

    Raises:
        ValueError: If interval format is invalid or out of range.
    """
    match = re.match(r"^(\d+)(m|h|d)$", interval.strip().lower())
    if not match:
        raise ValueError(
            f"Invalid interval: {interval}. Use format like '30m', '4h', '1d'"
        )
    value, unit = int(match.group(1)), match.group(2)

    if unit == "m":
        if value < 1 or value > 59:
            raise ValueError(f"Minutes must be 1-59, got {value}")
        return f"*/{value} * * * *"
    elif unit == "h":
        if value < 1 or value > 23:
            raise ValueError(f"Hours must be 1-23, got {value}")
        if value == 1:
            return "0 * * * *"
        return f"0 */{value} * * *"
    elif unit == "d":
        if value != 1:
            raise ValueError("Only '1d' (daily) is supported for day intervals")
        return "0 0 * * *"

    raise ValueError(f"Invalid interval unit: {unit}")


def get_current_crontab() -> str:
    """Get current user crontab, returning empty string if none."""
    result = subprocess.run(
        ["crontab", "-l"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return ""
    return result.stdout


def write_cron_env(project_root: str):
    """Write .cron-env file with current PATH so run_cycle.sh works in cron.

    Captures the current PATH (which includes node, python, etc.) at install
    time and writes it to a file that run_cycle.sh sources. This avoids
    fragile dynamic NVM/tool detection in the shell script.
    """
    env_path = os.path.join(project_root, ".cron-env")
    current_path = os.environ.get("PATH", "/usr/local/bin:/usr/bin:/bin")
    with open(env_path, "w") as f:
        f.write(f'export PATH="{current_path}"\n')


def install_crontab(cron_expr: str, script_path: str):
    """Install or update the trading cycle crontab entry."""
    current = get_current_crontab()
    # Remove existing polymarket entries
    lines = [l for l in current.splitlines() if CRON_MARKER not in l]
    # Add new entry with absolute path
    lines.append(f"{cron_expr} {script_path} {CRON_MARKER}")
    new_crontab = "\n".join(lines) + "\n"
    subprocess.run(
        ["crontab", "-"], input=new_crontab, text=True, check=True
    )


def remove_crontab():
    """Remove polymarket trading cycle from crontab."""
    current = get_current_crontab()
    lines = [l for l in current.splitlines() if CRON_MARKER not in l]
    new_crontab = "\n".join(lines) + "\n" if lines else ""
    if new_crontab.strip():
        subprocess.run(
            ["crontab", "-"], input=new_crontab, text=True, check=True
        )
    else:
        subprocess.run(["crontab", "-r"], capture_output=True)


def main():
    parser = argparse.ArgumentParser(
        description="Manage Polymarket trading cycle crontab schedule"
    )
    parser.add_argument(
        "--remove", action="store_true",
        help="Remove the trading cycle from crontab"
    )
    parser.add_argument(
        "--show", action="store_true",
        help="Show current crontab (do not modify)"
    )
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    if args.show:
        current = get_current_crontab()
        if current.strip():
            print(current)
        else:
            print("No crontab entries found.", file=sys.stderr)
        return

    if args.remove:
        remove_crontab()
        print("Polymarket trading schedule removed from crontab.")
        return

    # Load .env for CYCLE_INTERVAL
    load_dotenv(os.path.join(project_root, ".env"))
    interval = os.getenv("CYCLE_INTERVAL", "4h")

    try:
        cron_expr = interval_to_cron(interval)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    script_path = os.path.join(project_root, "run_cycle.sh")
    if not os.path.exists(script_path):
        print(f"Error: {script_path} not found. Create it first.", file=sys.stderr)
        sys.exit(1)

    # Write .cron-env with current PATH for run_cycle.sh to source
    write_cron_env(project_root)

    install_crontab(cron_expr, script_path)
    print(f"Schedule installed: {cron_expr} {script_path}")
    print(f"  Interval: {interval}")
    print(f"  Cron expression: {cron_expr}")
    print(f"  PATH snapshot: .cron-env written")
    print(f"  To remove: python tools/setup_schedule.py --remove")


if __name__ == "__main__":
    main()
