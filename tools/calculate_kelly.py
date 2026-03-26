#!/usr/bin/env python3
"""Calculate Kelly criterion position size for a trade."""

import argparse
import json
import os
import sys

# Ensure project root is on the path so lib/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.errors import EXIT_INVALID_ARG, error_exit
from lib.strategy import calculate_edge, calculate_position_size


def main():
    parser = argparse.ArgumentParser(
        description="Calculate Kelly criterion position size"
    )
    parser.add_argument(
        "--estimated-prob",
        type=float,
        required=True,
        dest="estimated_prob",
        help="Estimated true probability (0.0-1.0)",
    )
    parser.add_argument(
        "--market-price",
        type=float,
        required=True,
        dest="market_price",
        help="Current market price / price per share (0.0-1.0)",
    )
    parser.add_argument(
        "--bankroll",
        type=float,
        default=None,
        help="Available bankroll in USDC (default: MAX_TOTAL_EXPOSURE_USDC from .env)",
    )
    parser.add_argument(
        "--kelly-fraction",
        type=float,
        default=None,
        dest="kelly_fraction",
        help="Kelly fraction (default: KELLY_FRACTION from .env)",
    )
    parser.add_argument(
        "--max-position",
        type=float,
        default=None,
        dest="max_position_size_usdc",
        help="Max position size in USDC",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

    # Load config (.env defaults, CLI overrides)
    config = load_config(args)

    # Validate inputs
    if not (0 < args.estimated_prob < 1):
        error_exit(
            "Probability must be between 0 and 1 exclusive",
            "INVALID_ARG",
            EXIT_INVALID_ARG,
        )
    if not (0 < args.market_price < 1):
        error_exit(
            "Market price must be between 0 and 1 exclusive",
            "INVALID_ARG",
            EXIT_INVALID_ARG,
        )

    # Use CLI bankroll or config default
    bankroll = args.bankroll if args.bankroll is not None else config.max_total_exposure_usdc

    # Calculate position size
    position = calculate_position_size(
        prob=args.estimated_prob,
        price=args.market_price,
        bankroll=bankroll,
        kelly_fraction=config.kelly_fraction,
        max_position_usdc=config.max_position_size_usdc,
    )

    # Calculate edge
    edge = calculate_edge(args.estimated_prob, args.market_price)

    # Merge results
    output = {
        "estimated_prob": args.estimated_prob,
        "market_price": args.market_price,
        "edge": edge,
        "bankroll": bankroll,
        **position,
    }

    indent = 2 if args.pretty else None
    json.dump(output, sys.stdout, indent=indent)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
