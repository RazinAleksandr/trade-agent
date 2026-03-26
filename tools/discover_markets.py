#!/usr/bin/env python3
"""Discover active markets from Polymarket Gamma API."""

import argparse
import json
import os
import sys

# Ensure project root is on Python path so `lib` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.errors import error_exit, EXIT_API_ERROR
from lib.logging_setup import get_logger
from lib.market_data import fetch_active_markets
from lib.signals import register_shutdown_handler


def main():
    parser = argparse.ArgumentParser(
        description="Discover active Polymarket markets"
    )
    parser.add_argument(
        "--min-volume",
        type=float,
        dest="min_volume_24h",
        help="Minimum 24h volume in USDC",
    )
    parser.add_argument(
        "--min-liquidity",
        type=float,
        dest="min_liquidity",
        help="Minimum liquidity in USDC",
    )
    parser.add_argument(
        "--limit",
        type=int,
        dest="max_markets_per_cycle",
        help="Maximum number of markets to return",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("discover_markets", config)

    try:
        markets = fetch_active_markets(
            gamma_api_url=config.gamma_api_url,
            min_volume=config.min_volume_24h,
            min_liquidity=config.min_liquidity,
            limit=config.max_markets_per_cycle,
        )
        indent = 2 if args.pretty else None
        json.dump([m.to_dict() for m in markets], sys.stdout, indent=indent)
        sys.stdout.write("\n")
    except Exception as e:
        log.error(f"Discovery failed: {e}")
        error_exit(str(e), "DISCOVERY_FAILED", EXIT_API_ERROR)


if __name__ == "__main__":
    main()
