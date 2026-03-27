#!/usr/bin/env python3
"""Live trading gate -- verify paper P&L before enabling live mode.

Checks that:
1. At least MIN_PAPER_CYCLES paper trading cycles have been completed
2. Aggregate paper P&L is positive

If conditions are met, requires typing 'CONFIRM LIVE' to write a gate-pass
file that execute_trade.py checks before placing live orders.

Usage:
    python tools/enable_live.py          # Verify and enable
    python tools/enable_live.py --revoke # Remove gate pass (re-lock)
    python tools/enable_live.py --status # Check gate status only
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.db import DataStore

GATE_PASS_FILE = ".live-gate-pass"


def get_project_root() -> str:
    """Return the project root directory (parent of tools/)."""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(
        description="Verify paper P&L and enable live trading"
    )
    parser.add_argument(
        "--revoke", action="store_true",
        help="Remove gate pass (disable live trading)"
    )
    parser.add_argument(
        "--status", action="store_true",
        help="Check gate status without modifying anything"
    )
    args = parser.parse_args()

    project_root = get_project_root()
    gate_path = os.path.join(project_root, GATE_PASS_FILE)

    # Handle --revoke
    if args.revoke:
        if os.path.exists(gate_path):
            os.remove(gate_path)
            print("Gate pass removed. Live trading disabled.", file=sys.stderr)
        else:
            print("No gate pass found. Live trading already disabled.",
                  file=sys.stderr)
        return

    # Load config and connect to database
    config = load_config()
    reports_dir = os.path.join(project_root, "state", "reports")
    store = DataStore(db_path=config.db_path)

    try:
        stats = store.get_paper_cycle_stats(reports_dir=reports_dir)
        cycles = stats["cycle_count"]
        pnl = stats["total_pnl"]

        # Display verification summary
        print(f"\n{'='*50}", file=sys.stderr)
        print("LIVE TRADING GATE VERIFICATION", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)
        print(f"Completed paper cycles: {cycles}", file=sys.stderr)
        print(f"Minimum required:       {config.min_paper_cycles}",
              file=sys.stderr)
        print(f"Aggregate paper P&L:    ${pnl:.2f}", file=sys.stderr)
        print(f"Gate pass file:         {GATE_PASS_FILE}", file=sys.stderr)
        print(f"Gate pass exists:       {os.path.exists(gate_path)}",
              file=sys.stderr)
        print(f"{'='*50}\n", file=sys.stderr)

        # Handle --status (display only)
        if args.status:
            if os.path.exists(gate_path):
                print("Status: LIVE TRADING ENABLED (gate pass exists)",
                      file=sys.stderr)
            else:
                print("Status: LIVE TRADING DISABLED (no gate pass)",
                      file=sys.stderr)
            return

        # Check conditions
        if cycles < config.min_paper_cycles:
            remaining = config.min_paper_cycles - cycles
            print(
                f"BLOCKED: Need {remaining} more paper cycle(s) "
                f"(have {cycles}, need {config.min_paper_cycles}).",
                file=sys.stderr,
            )
            sys.exit(1)

        if pnl <= 0:
            print(
                f"BLOCKED: Paper P&L must be positive (currently ${pnl:.2f}).",
                file=sys.stderr,
            )
            sys.exit(1)

        # All conditions met -- request confirmation
        print(
            "All conditions met. To enable live trading, type CONFIRM LIVE:",
            file=sys.stderr,
        )
        confirmation = input("> ").strip()

        if confirmation != "CONFIRM LIVE":
            print("Confirmation failed. Live trading NOT enabled.",
                  file=sys.stderr)
            sys.exit(1)

        # Write gate pass file
        gate_data = {
            "enabled_at": datetime.now(timezone.utc).isoformat(),
            "cycles_at_gate": cycles,
            "pnl_at_gate": pnl,
            "min_paper_cycles": config.min_paper_cycles,
        }
        with open(gate_path, "w") as f:
            json.dump(gate_data, f, indent=2)
            f.write("\n")

        print(f"\nGate pass written to {GATE_PASS_FILE}", file=sys.stderr)
        print(
            "Live trading enabled. Delete the file to re-lock.",
            file=sys.stderr,
        )

        # Output gate data as JSON to stdout (tool output pattern)
        json.dump(gate_data, sys.stdout, indent=2)
        sys.stdout.write("\n")

    finally:
        store.close()


if __name__ == "__main__":
    main()
