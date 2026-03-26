#!/usr/bin/env python3
"""Get current portfolio with open positions and P&L."""

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
from lib.portfolio import check_risk_limits, get_portfolio_summary
from lib.signals import register_shutdown_handler


def main():
    parser = argparse.ArgumentParser(
        description="Get current portfolio with open positions and P&L"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    parser.add_argument(
        "--include-risk",
        action="store_true",
        dest="include_risk",
        help="Include risk limit checks in output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("get_portfolio", config)

    store = DataStore(db_path=config.db_path)
    try:
        result = get_portfolio_summary(
            store=store,
            gamma_api_url=config.gamma_api_url,
            max_total_exposure_usdc=config.max_total_exposure_usdc,
        )

        if args.include_risk:
            risk = check_risk_limits(
                store,
                config.max_total_exposure_usdc,
                config.max_position_size_usdc,
            )
            result["risk"] = risk

        indent = 2 if args.pretty else None
        json.dump(result, sys.stdout, indent=indent)
        sys.stdout.write("\n")
    except Exception as e:
        log.error(f"Portfolio fetch failed: {e}")
        error_exit(str(e), "PORTFOLIO_FAILED", EXIT_API_ERROR)
    finally:
        store.close()


if __name__ == "__main__":
    main()
