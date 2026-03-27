"""Portfolio tracking, P&L calculation, risk checks, and resolved market detection.

Cherry-picked and adapted from v1 portfolio.py:
- Stateless functions (not a class) for CLI compatibility
- Explicit parameter passing (no global config import)
- Unrealized P&L from live Gamma API prices
- Resolved market detection via market.closed flag
- Risk limit warnings at 90% utilization
"""

from lib.db import DataStore
from lib.fees import calculate_fee_per_share
from lib.logging_setup import get_logger
from lib.market_data import fetch_market_by_id

log = get_logger("portfolio")


def get_portfolio_summary(
    store: DataStore,
    gamma_api_url: str,
    max_total_exposure_usdc: float = 200.0,
) -> dict:
    """Get current portfolio state with live prices and unrealized P&L.

    Fetches current market prices from Gamma API for each open position,
    calculates unrealized P&L, and updates the database.

    Args:
        store: DataStore instance for position queries and updates.
        gamma_api_url: Base URL for Gamma API.
        max_total_exposure_usdc: Maximum total exposure for capacity calculation.

    Returns:
        Dict with open_positions count, total_exposure_usdc, remaining_capacity,
        positions list, and strategy stats (total_trades, win_rate, total_pnl, avg_edge).
    """
    positions = store.get_open_positions()
    total_exposure = store.get_total_exposure()
    stats = store.get_strategy_stats()

    for pos in positions:
        market = fetch_market_by_id(gamma_api_url, pos["market_id"])
        if not market:
            continue

        if pos["side"] == "YES":
            current_price = market.yes_price
        else:
            current_price = market.no_price

        # Estimate exit fee for conservative unrealized P&L
        exit_fee = calculate_fee_per_share(current_price, market.category)
        unrealized_pnl = (current_price - exit_fee - pos["avg_price"]) * pos["size"]

        # Update position dict for return value
        pos["current_price"] = current_price
        pos["unrealized_pnl"] = unrealized_pnl

        # Persist updated price and P&L to database
        store.conn.execute(
            "UPDATE positions SET current_price = ?, unrealized_pnl = ? WHERE id = ?",
            (current_price, unrealized_pnl, pos["id"]),
        )

    store.conn.commit()
    log.info(f"Updated prices for {len(positions)} positions")

    return {
        "open_positions": len(positions),
        "total_exposure_usdc": total_exposure,
        "remaining_capacity": max_total_exposure_usdc - total_exposure,
        "positions": positions,
        **stats,
    }


def check_resolved_markets(
    store: DataStore,
    gamma_api_url: str,
) -> list[dict]:
    """Check for resolved markets and close positions with realized P&L.

    Queries all open positions, fetches their market status from Gamma API,
    and closes any positions where the market has resolved (market.closed == True).

    Args:
        store: DataStore instance for position queries and updates.
        gamma_api_url: Base URL for Gamma API.

    Returns:
        List of dicts for each resolved position, containing market_id, question,
        side, exit_price, avg_price, size, and realized_pnl.
    """
    positions = store.get_open_positions()
    resolved = []

    for pos in positions:
        market = fetch_market_by_id(gamma_api_url, pos["market_id"])
        if not market:
            continue

        if market.closed:
            # Determine exit price based on position side
            if pos["side"] == "YES":
                exit_price = market.yes_price
            else:
                exit_price = market.no_price

            store.close_position(pos["market_id"], exit_price)

            realized_pnl = round((exit_price - pos["avg_price"]) * pos["size"], 2)
            resolved.append({
                "market_id": pos["market_id"],
                "question": pos.get("question", ""),
                "side": pos["side"],
                "exit_price": exit_price,
                "avg_price": pos["avg_price"],
                "size": pos["size"],
                "realized_pnl": realized_pnl,
            })

            log.info(
                f"Market resolved: '{pos.get('question', '')[:50]}' -- "
                f"exit price: {exit_price:.2f}, realized PnL: {realized_pnl:.2f}"
            )

    return resolved


def check_risk_limits(
    store: DataStore,
    max_total_exposure_usdc: float = 200.0,
    max_position_size_usdc: float = 50.0,
) -> dict:
    """Check current risk exposure against configured limits.

    Warns when total exposure or individual position sizes exceed 90%
    of their respective limits.

    Args:
        store: DataStore instance for position queries.
        max_total_exposure_usdc: Maximum total portfolio exposure.
        max_position_size_usdc: Maximum single position size.

    Returns:
        Dict with total_exposure, max_exposure, utilization ratio,
        num_positions, and a list of warning strings.
    """
    total_exposure = store.get_total_exposure()
    positions = store.get_open_positions()

    warnings = []

    if total_exposure > max_total_exposure_usdc * 0.9:
        warnings.append(
            f"Total exposure ${total_exposure:.2f} near limit "
            f"${max_total_exposure_usdc:.2f}"
        )

    for pos in positions:
        if pos["cost_basis"] > max_position_size_usdc * 0.9:
            warnings.append(
                f"Position '{pos.get('question', '')[:40]}' size "
                f"${pos['cost_basis']:.2f} near limit "
                f"${max_position_size_usdc:.2f}"
            )

    if warnings:
        for w in warnings:
            log.warning(f"RISK: {w}")

    return {
        "total_exposure": total_exposure,
        "max_exposure": max_total_exposure_usdc,
        "utilization": total_exposure / max_total_exposure_usdc if max_total_exposure_usdc > 0 else 0,
        "num_positions": len(positions),
        "warnings": warnings,
    }
