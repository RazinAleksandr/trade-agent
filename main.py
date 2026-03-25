#!/usr/bin/env python3
"""
Autonomous Polymarket Trading Agent

Loop: discover markets → analyze with OpenAI → calculate edge →
      size positions → trade → monitor → update strategy
"""

import time
import signal
import sys
from datetime import datetime, timezone

import config
from logger_setup import get_logger, log_decision
from data_store import DataStore
from market_discovery import fetch_active_markets, fetch_market_by_id
from market_analyzer import batch_analyze
from strategy import generate_signals
from trader import Trader
from portfolio import PortfolioManager

log = get_logger("main")

# Graceful shutdown
shutdown_requested = False


def signal_handler(sig, frame):
    global shutdown_requested
    log.info("Shutdown requested...")
    shutdown_requested = True


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def run_trading_cycle(trader: Trader, portfolio: PortfolioManager, store: DataStore) -> dict:
    """Execute one full trading cycle."""
    cycle_start = datetime.now(timezone.utc)
    results = {
        "markets_discovered": 0,
        "markets_analyzed": 0,
        "signals_generated": 0,
        "trades_executed": 0,
        "errors": [],
    }

    # Step 1: Discover markets
    log.info("Step 1: Discovering markets...")
    try:
        markets = fetch_active_markets()
        results["markets_discovered"] = len(markets)
        log.info(f"Found {len(markets)} tradable markets")
    except Exception as e:
        log.error(f"Market discovery failed: {e}")
        results["errors"].append(f"discovery: {e}")
        return results

    if not markets:
        log.info("No markets found matching criteria")
        return results

    # Step 2: Snapshot market data
    log.info("Step 2: Recording market snapshots...")
    for market in markets:
        store.record_market_snapshot(
            market_id=market.id,
            question=market.question,
            yes_price=market.yes_price,
            no_price=market.no_price,
            volume_24h=market.volume_24h,
            liquidity=market.liquidity,
            end_date=market.end_date,
        )

    # Step 3: Analyze with OpenAI
    log.info("Step 3: Analyzing markets with OpenAI...")
    try:
        analyses = batch_analyze(markets)
        results["markets_analyzed"] = len(analyses)
        log.info(f"Analyzed {len(analyses)} markets")
    except Exception as e:
        log.error(f"Analysis failed: {e}")
        results["errors"].append(f"analysis: {e}")
        return results

    # Step 4: Generate trade signals
    log.info("Step 4: Generating trade signals...")
    try:
        signals = generate_signals(analyses, store)
        results["signals_generated"] = len(signals)
        log.info(f"Generated {len(signals)} signals")
    except Exception as e:
        log.error(f"Signal generation failed: {e}")
        results["errors"].append(f"signals: {e}")
        return results

    # Step 5: Execute trades
    log.info("Step 5: Executing trades...")
    for signal in signals:
        try:
            # Fetch fresh market data for execution
            market = fetch_market_by_id(signal.market_id)
            if not market:
                log.warning(f"Could not fetch market {signal.market_id} for execution")
                continue

            result = trader.execute_signal(signal, market)
            if result.success:
                results["trades_executed"] += 1
                log.info(f"Trade executed: {result.order_id}")
            else:
                log.warning(f"Trade failed: {result.message}")
        except Exception as e:
            log.error(f"Trade execution error: {e}")
            results["errors"].append(f"trade: {e}")

    # Step 6: Update portfolio
    log.info("Step 6: Updating portfolio...")
    try:
        portfolio.update_position_prices()
        portfolio.check_for_resolved_markets()
        risk = portfolio.check_risk_limits()
    except Exception as e:
        log.error(f"Portfolio update failed: {e}")
        results["errors"].append(f"portfolio: {e}")

    # Log cycle results
    elapsed = (datetime.now(timezone.utc) - cycle_start).total_seconds()
    log_decision(log, "cycle_complete", {
        **results,
        "elapsed_seconds": elapsed,
    })

    return results


def run_strategy_update(store: DataStore):
    """Analyze past performance and log strategy metrics."""
    stats = store.get_strategy_stats()
    if stats["total_trades"] == 0:
        return

    now = datetime.now(timezone.utc).isoformat()
    store.conn.execute(
        """INSERT INTO strategy_metrics
           (timestamp, total_trades, win_rate, total_pnl, avg_edge, metadata)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (now, stats["total_trades"], stats["win_rate"],
         stats["total_pnl"], stats["avg_edge"], None)
    )
    store.conn.commit()

    log.info(
        f"Strategy update: {stats['total_trades']} trades, "
        f"win rate {stats['win_rate']:.1%}, "
        f"P&L ${stats['total_pnl']:.2f}, "
        f"avg edge {stats['avg_edge']:.2%}"
    )


def main():
    log.info("=" * 60)
    log.info("Polymarket Autonomous Trading Agent")
    log.info(f"Mode: {'PAPER' if config.PAPER_TRADING else 'LIVE'}")
    log.info(f"Loop interval: {config.LOOP_INTERVAL}s")
    log.info(f"Max exposure: ${config.MAX_TOTAL_EXPOSURE_USDC}")
    log.info(f"Min edge: {config.MIN_EDGE_THRESHOLD:.0%}")
    log.info(f"Kelly fraction: {config.KELLY_FRACTION}")
    log.info("=" * 60)

    # Validate config
    if not config.OPENAI_API_KEY:
        log.error("OPENAI_API_KEY not set. Cannot run analysis.")
        sys.exit(1)

    if not config.PAPER_TRADING and not config.PRIVATE_KEY:
        log.error("PRIVATE_KEY not set for live trading mode.")
        sys.exit(1)

    # Initialize components
    store = DataStore()
    trader = Trader(store)
    portfolio = PortfolioManager(store)

    cycle_count = 0

    try:
        while not shutdown_requested:
            cycle_count += 1
            log.info(f"\n{'─' * 40}")
            log.info(f"CYCLE {cycle_count} — {datetime.now(timezone.utc).isoformat()}")
            log.info(f"{'─' * 40}")

            # Run trading cycle
            results = run_trading_cycle(trader, portfolio, store)

            # Print portfolio summary
            portfolio.print_portfolio()

            # Periodic strategy review (every 5 cycles)
            if cycle_count % 5 == 0:
                run_strategy_update(store)

            if results["errors"]:
                log.warning(f"Cycle had {len(results['errors'])} error(s)")

            # Wait for next cycle
            if not shutdown_requested:
                log.info(f"Next cycle in {config.LOOP_INTERVAL}s...")
                for _ in range(config.LOOP_INTERVAL):
                    if shutdown_requested:
                        break
                    time.sleep(1)

    except KeyboardInterrupt:
        log.info("Interrupted by user")
    finally:
        # Final summary
        portfolio.print_portfolio()
        run_strategy_update(store)
        store.close()
        log.info("Agent shutdown complete")


if __name__ == "__main__":
    main()
