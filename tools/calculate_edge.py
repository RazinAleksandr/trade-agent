#!/usr/bin/env python3
"""Calculate edge for a market given estimated probability and market price."""

import argparse
import json
import os
import sys

# Ensure project root is on the path so lib/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.errors import EXIT_INVALID_ARG, error_exit
from lib.strategy import calculate_edge


def main():
    parser = argparse.ArgumentParser(
        description="Calculate edge (estimated probability - market price)"
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
        help="Current market price (0.0-1.0)",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output",
    )
    args = parser.parse_args()

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

    edge = calculate_edge(args.estimated_prob, args.market_price)

    if edge > 0:
        direction = "BUY_YES"
    elif edge < 0:
        direction = "BUY_NO"
    else:
        direction = "NO_EDGE"

    output = {
        "estimated_prob": args.estimated_prob,
        "market_price": args.market_price,
        "edge": edge,
        "edge_pct": f"{edge * 100:.2f}%",
        "direction": direction,
    }

    indent = 2 if args.pretty else None
    json.dump(output, sys.stdout, indent=indent)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
