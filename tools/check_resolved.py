#!/usr/bin/env python3
"""Check for resolved markets and finalize P&L."""

import argparse
import json
import os
import sys

# Ensure project root is on Python path so `lib` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.db import DataStore
from lib.errors import error_exit, EXIT_API_ERROR
from lib.logging_setup import get_logger
from lib.portfolio import check_resolved_markets
from lib.signals import register_shutdown_handler


def main():
    parser = argparse.ArgumentParser(
        description="Check for resolved markets and finalize P&L"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("check_resolved", config)

    store = DataStore(db_path=config.db_path)
    try:
        resolved = check_resolved_markets(
            store=store,
            gamma_api_url=config.gamma_api_url,
        )

        result = {
            "resolved_count": len(resolved),
            "resolved_markets": resolved,
        }

        indent = 2 if args.pretty else None
        json.dump(result, sys.stdout, indent=indent)
        sys.stdout.write("\n")
    except Exception as e:
        log.error(f"Resolved check failed: {e}")
        error_exit(str(e), "RESOLVED_CHECK_FAILED", EXIT_API_ERROR)
    finally:
        store.close()


if __name__ == "__main__":
    main()
