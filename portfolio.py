from data_store import DataStore
from market_discovery import fetch_market_by_id, Market
import config
from logger_setup import get_logger

log = get_logger("portfolio")


class PortfolioManager:
    def __init__(self, store: DataStore):
        self.store = store

    def get_portfolio_summary(self) -> dict:
        """Get current portfolio state."""
        positions = self.store.get_open_positions()
        total_exposure = self.store.get_total_exposure()
        stats = self.store.get_strategy_stats()

        return {
            "open_positions": len(positions),
            "total_exposure_usdc": total_exposure,
            "remaining_capacity": config.MAX_TOTAL_EXPOSURE_USDC - total_exposure,
            "positions": positions,
            **stats,
        }

    def update_position_prices(self):
        """Update current prices for open positions from market data."""
        positions = self.store.get_open_positions()
        for pos in positions:
            market = fetch_market_by_id(pos["market_id"])
            if not market:
                continue

            if pos["side"] == "YES":
                current_price = market.yes_price
            else:
                current_price = market.no_price

            unrealized = (current_price - pos["avg_price"]) * pos["size"]

            self.store.conn.execute(
                """UPDATE positions SET current_price = ?, unrealized_pnl = ?
                   WHERE id = ?""",
                (current_price, unrealized, pos["id"])
            )
        self.store.conn.commit()
        log.info(f"Updated prices for {len(positions)} positions")

    def check_for_resolved_markets(self):
        """Check if any open positions have resolved and close them."""
        positions = self.store.get_open_positions()
        for pos in positions:
            market = fetch_market_by_id(pos["market_id"])
            if not market:
                continue

            if market.closed:
                # Determine resolution price
                if pos["side"] == "YES":
                    exit_price = market.yes_price
                else:
                    exit_price = market.no_price

                self.store.close_position(pos["market_id"], exit_price)
                log.info(
                    f"Market resolved: '{pos['question'][:50]}' — "
                    f"exit price: {exit_price:.2f}"
                )

    def check_risk_limits(self) -> dict:
        """Check current risk exposure against limits."""
        total_exposure = self.store.get_total_exposure()
        positions = self.store.get_open_positions()

        warnings = []
        if total_exposure > config.MAX_TOTAL_EXPOSURE_USDC * 0.9:
            warnings.append(
                f"Total exposure ${total_exposure:.2f} near limit "
                f"${config.MAX_TOTAL_EXPOSURE_USDC:.2f}"
            )

        for pos in positions:
            if pos["cost_basis"] > config.MAX_POSITION_SIZE_USDC * 0.9:
                warnings.append(
                    f"Position '{pos['question'][:40]}' size "
                    f"${pos['cost_basis']:.2f} near limit"
                )

        if warnings:
            for w in warnings:
                log.warning(f"RISK: {w}")

        return {
            "total_exposure": total_exposure,
            "max_exposure": config.MAX_TOTAL_EXPOSURE_USDC,
            "utilization": total_exposure / config.MAX_TOTAL_EXPOSURE_USDC if config.MAX_TOTAL_EXPOSURE_USDC > 0 else 0,
            "num_positions": len(positions),
            "warnings": warnings,
        }

    def print_portfolio(self):
        """Print a formatted portfolio summary."""
        summary = self.get_portfolio_summary()
        risk = self.check_risk_limits()

        print("\n" + "=" * 60)
        print("PORTFOLIO SUMMARY")
        print("=" * 60)
        print(f"Mode: {'PAPER' if config.PAPER_TRADING else 'LIVE'}")
        print(f"Open Positions: {summary['open_positions']}")
        print(f"Total Exposure: ${summary['total_exposure_usdc']:.2f} / ${config.MAX_TOTAL_EXPOSURE_USDC:.2f}")
        print(f"Utilization: {risk['utilization']:.1%}")
        print(f"Total Trades: {summary['total_trades']}")
        print(f"Win Rate: {summary['win_rate']:.1%}")
        print(f"Total P&L: ${summary['total_pnl']:.2f}")

        if summary["positions"]:
            print("\nOPEN POSITIONS:")
            print("-" * 60)
            for pos in summary["positions"]:
                pnl = pos.get("unrealized_pnl", 0) or 0
                print(
                    f"  {pos['side']:3s} | "
                    f"${pos['cost_basis']:.2f} | "
                    f"PnL: ${pnl:.2f} | "
                    f"{pos['question'][:45]}"
                )

        if risk["warnings"]:
            print("\nWARNINGS:")
            for w in risk["warnings"]:
                print(f"  ⚠ {w}")

        print("=" * 60 + "\n")
