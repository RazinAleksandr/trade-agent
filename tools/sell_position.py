#!/usr/bin/env python3
"""Sell (close or reduce) an existing position on Polymarket."""

import argparse
import json
import os
import sys

# Ensure project root is on Python path so `lib` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.db import DataStore
from lib.errors import error_exit, EXIT_INVALID_ARG, EXIT_API_ERROR, EXIT_CONFIG_ERROR, EXIT_TRADE_FAILED
from lib.logging_setup import get_logger
from lib.signals import register_shutdown_handler
from lib.trading import execute_paper_sell, execute_live_sell


def main():
    parser = argparse.ArgumentParser(
        description="Sell (close or reduce) an existing position on Polymarket"
    )
    parser.add_argument(
        "--market-id",
        type=str,
        required=True,
        dest="market_id",
        help="Market ID of the position to sell",
    )
    parser.add_argument(
        "--token-id",
        type=str,
        required=True,
        dest="token_id",
        help="CLOB token ID for the outcome being sold",
    )
    parser.add_argument(
        "--side",
        type=str,
        required=True,
        choices=["YES", "NO"],
        help="Side being sold (YES or NO)",
    )
    parser.add_argument(
        "--size",
        type=float,
        required=True,
        help="Number of shares to sell",
    )
    parser.add_argument(
        "--price",
        type=float,
        default=None,
        help="Limit price (required for live, ignored for paper which uses orderbook)",
    )
    parser.add_argument(
        "--question",
        type=str,
        default="",
        help="Market question (for record-keeping)",
    )
    parser.add_argument(
        "--reasoning",
        type=str,
        default="",
        help="Sell reasoning (for record-keeping)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default="other",
        help="Market category for fee calculation (default: other)",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute as live sell (default: paper)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("sell_position", config)

    store = DataStore(db_path=config.db_path)
    try:
        # Validate that we have an open position to sell
        positions = store.get_open_positions()
        matching = [p for p in positions if p["market_id"] == args.market_id]
        if not matching:
            error_exit(
                f"No open position for market {args.market_id}",
                "NO_POSITION",
                EXIT_INVALID_ARG,
            )
        held_size = matching[0]["size"]
        if args.size > held_size + 0.001:
            error_exit(
                f"Sell size {args.size} exceeds held size {held_size}",
                "SIZE_EXCEEDED",
                EXIT_INVALID_ARG,
            )

        is_live = args.live or not config.paper_trading

        if is_live:
            gate_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                ".live-gate-pass"
            )
            if not os.path.exists(gate_path):
                error_exit(
                    "Live trading blocked: no gate pass. "
                    "Run 'python tools/enable_live.py' to verify paper P&L and enable live trading.",
                    "GATE_BLOCKED",
                    EXIT_CONFIG_ERROR,
                )

            if not config.private_key:
                error_exit(
                    "PRIVATE_KEY required for live trading",
                    "CONFIG_ERROR",
                    EXIT_CONFIG_ERROR,
                )

            if args.price is None:
                error_exit(
                    "--price required for live selling",
                    "INVALID_ARG",
                    EXIT_INVALID_ARG,
                )

            result = execute_live_sell(
                market_id=args.market_id,
                question=args.question,
                side=args.side,
                token_id=args.token_id,
                price=args.price,
                size=args.size,
                host=config.polymarket_host,
                private_key=config.private_key,
                chain_id=config.chain_id,
                store=store,
                reasoning=args.reasoning,
            )
        else:
            result = execute_paper_sell(
                market_id=args.market_id,
                question=args.question,
                side=args.side,
                token_id=args.token_id,
                size=args.size,
                host=config.polymarket_host,
                store=store,
                reasoning=args.reasoning,
                category=args.category,
            )

        indent = 2 if args.pretty else None
        json.dump(result.to_dict(), sys.stdout, indent=indent)
        sys.stdout.write("\n")

    except ValueError as e:
        log.error(f"Sell failed: {e}")
        error_exit(str(e), "SELL_FAILED", EXIT_TRADE_FAILED)
    except Exception as e:
        log.error(f"Sell failed: {e}")
        error_exit(str(e), "SELL_FAILED", EXIT_TRADE_FAILED)
    finally:
        store.close()


if __name__ == "__main__":
    main()
