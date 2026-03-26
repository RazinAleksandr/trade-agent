#!/usr/bin/env python3
"""Get orderbook prices for a Polymarket token."""

import argparse
import json
import os
import sys

# Ensure project root is on Python path so `lib` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.errors import error_exit, EXIT_API_ERROR
from lib.logging_setup import get_logger
from lib.pricing import get_best_bid, get_best_ask
from lib.signals import register_shutdown_handler


def main():
    parser = argparse.ArgumentParser(
        description="Get current orderbook prices for a Polymarket token"
    )
    parser.add_argument(
        "--token-id",
        type=str,
        required=True,
        dest="token_id",
        help="CLOB token ID",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("get_prices", config)

    try:
        bid = get_best_bid(args.token_id, config.polymarket_host)
        ask = get_best_ask(args.token_id, config.polymarket_host)

        output = {
            "token_id": args.token_id,
            "best_bid": bid,
            "best_ask": ask,
            "spread": round(ask - bid, 6),
            "mid_price": round((bid + ask) / 2, 6),
        }

        indent = 2 if args.pretty else None
        json.dump(output, sys.stdout, indent=indent)
        sys.stdout.write("\n")
    except ValueError as e:
        log.error(f"Price fetch failed: {e}")
        error_exit(str(e), "NO_LIQUIDITY", EXIT_API_ERROR)
    except Exception as e:
        log.error(f"Price fetch failed: {e}")
        error_exit(str(e), "PRICE_FETCH_FAILED", EXIT_API_ERROR)


if __name__ == "__main__":
    main()
