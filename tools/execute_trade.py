#!/usr/bin/env python3
"""Execute a trade (paper or live) on Polymarket."""

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
from lib.trading import execute_paper_trade, execute_live_trade


def main():
    parser = argparse.ArgumentParser(
        description="Execute a trade (paper or live) on Polymarket"
    )
    parser.add_argument(
        "--market-id",
        type=str,
        required=True,
        dest="market_id",
        help="Market ID",
    )
    parser.add_argument(
        "--token-id",
        type=str,
        required=True,
        dest="token_id",
        help="CLOB token ID for the outcome",
    )
    parser.add_argument(
        "--side",
        type=str,
        required=True,
        choices=["YES", "NO"],
        help="Side to buy (YES or NO)",
    )
    parser.add_argument(
        "--size",
        type=float,
        required=True,
        help="Number of shares",
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
        "--condition-id",
        type=str,
        default="",
        dest="condition_id",
        help="Market condition ID",
    )
    parser.add_argument(
        "--estimated-prob",
        type=float,
        default=0,
        dest="estimated_prob",
        help="Estimated probability (for record-keeping)",
    )
    parser.add_argument(
        "--edge",
        type=float,
        default=0,
        help="Calculated edge (for record-keeping)",
    )
    parser.add_argument(
        "--reasoning",
        type=str,
        default="",
        help="Trade reasoning (for record-keeping)",
    )
    parser.add_argument(
        "--neg-risk",
        action="store_true",
        dest="neg_risk",
        help="Market uses neg-risk exchange",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Execute as live trade (default: paper)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )

    args = parser.parse_args()
    config = load_config(args)
    register_shutdown_handler()
    log = get_logger("execute_trade", config)

    store = DataStore(db_path=config.db_path)
    try:
        is_live = args.live or not config.paper_trading

        if is_live:
            # Gate-pass check (D-08: SAFE-03)
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

            # Live trading requires private key (D-11)
            if not config.private_key:
                error_exit(
                    "PRIVATE_KEY required for live trading",
                    "CONFIG_ERROR",
                    EXIT_CONFIG_ERROR,
                )

            # Live trading requires explicit price
            if args.price is None:
                error_exit(
                    "--price required for live trading",
                    "INVALID_ARG",
                    EXIT_INVALID_ARG,
                )

            result = execute_live_trade(
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
                condition_id=args.condition_id,
                estimated_prob=args.estimated_prob,
                edge=args.edge,
                reasoning=args.reasoning,
                neg_risk=args.neg_risk,
            )
        else:
            result = execute_paper_trade(
                market_id=args.market_id,
                question=args.question,
                side=args.side,
                token_id=args.token_id,
                size=args.size,
                host=config.polymarket_host,
                store=store,
                condition_id=args.condition_id,
                estimated_prob=args.estimated_prob,
                edge=args.edge,
                reasoning=args.reasoning,
                neg_risk=args.neg_risk,
            )

        indent = 2 if args.pretty else None
        json.dump(result.to_dict(), sys.stdout, indent=indent)
        sys.stdout.write("\n")

    except ValueError as e:
        # CLOB API unreachable (D-10)
        log.error(f"Price unavailable: {e}")
        error_exit(str(e), "PRICE_UNAVAILABLE", EXIT_API_ERROR)
    except Exception as e:
        log.error(f"Trade failed: {e}")
        error_exit(str(e), "TRADE_FAILED", EXIT_TRADE_FAILED)
    finally:
        store.close()


if __name__ == "__main__":
    main()
