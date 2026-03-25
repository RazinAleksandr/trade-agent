#!/usr/bin/env python3
"""Smoke tests for the trading agent pipeline."""

import os
import sys
import tempfile

# Use temp DB for tests
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["PAPER_TRADING"] = "true"
os.environ["LOG_FILE"] = tempfile.mktemp(suffix=".log")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_config():
    import config
    assert config.PAPER_TRADING is True
    assert config.CHAIN_ID == 137
    assert config.KELLY_FRACTION > 0
    print("✓ config OK")


def test_data_store():
    from data_store import DataStore
    store = DataStore()

    # Record a trade
    trade_id = store.record_trade(
        market_id="test-123",
        question="Will it rain tomorrow?",
        side="YES",
        price=0.65,
        size=10.0,
        is_paper=True,
        edge=0.10,
    )
    assert trade_id > 0

    # Upsert position
    store.upsert_position(
        market_id="test-123",
        question="Will it rain tomorrow?",
        side="YES",
        price=0.65,
        size=10.0,
    )

    positions = store.get_open_positions()
    assert len(positions) == 1
    assert positions[0]["market_id"] == "test-123"

    exposure = store.get_total_exposure()
    assert exposure == 6.5  # 0.65 * 10

    # Record decision
    store.record_decision(
        market_id="test-123",
        question="Will it rain tomorrow?",
        decision_type="trade",
        market_price=0.55,
        estimated_prob=0.65,
        edge=0.10,
        kelly_size=5.0,
        action="BUY YES",
    )

    # Close position
    store.close_position("test-123", exit_price=0.75)
    positions = store.get_open_positions()
    assert len(positions) == 0

    stats = store.get_strategy_stats()
    assert stats["total_trades"] == 1

    store.close()
    print("✓ data_store OK")


def test_market_discovery():
    from market_discovery import fetch_active_markets
    markets = fetch_active_markets(limit=3, min_volume=100, min_liquidity=50)
    assert len(markets) > 0
    m = markets[0]
    assert m.question
    assert m.yes_token_id
    assert 0 < m.yes_price < 1
    print(f"✓ market_discovery OK ({len(markets)} markets)")


def test_strategy():
    from strategy import kelly_criterion, TradeSignal

    # Kelly: 60% chance, buying at 0.50
    k = kelly_criterion(0.60, 0.50, fraction=1.0)
    assert k > 0, f"Expected positive Kelly, got {k}"

    # Kelly: no edge (50% at 0.50)
    k = kelly_criterion(0.50, 0.50, fraction=1.0)
    assert k == 0, f"Expected zero Kelly, got {k}"

    # Kelly: negative edge
    k = kelly_criterion(0.40, 0.50, fraction=1.0)
    assert k == 0, f"Expected zero Kelly for negative edge, got {k}"

    print("✓ strategy OK")


def test_portfolio():
    from data_store import DataStore
    from portfolio import PortfolioManager
    store = DataStore()
    pm = PortfolioManager(store)
    summary = pm.get_portfolio_summary()
    assert "open_positions" in summary
    risk = pm.check_risk_limits()
    assert "total_exposure" in risk
    store.close()
    print("✓ portfolio OK")


def test_strategy_stats_empty():
    from data_store import DataStore
    store = DataStore(db_path=tempfile.mktemp(suffix=".db"))
    stats = store.get_strategy_stats()
    assert stats["total_trades"] == 0
    assert stats["avg_edge"] == 0
    assert "avg_edge" in stats, "avg_edge key missing from empty stats"
    store.close()
    print("✓ strategy_stats_empty OK")


def test_pnl_from_resolved_positions():
    from data_store import DataStore
    store = DataStore(db_path=tempfile.mktemp(suffix=".db"))

    # Record a trade
    store.record_trade(
        market_id="pnl-test-001",
        question="PnL test market?",
        side="YES",
        price=0.50,
        size=10.0,
        is_paper=True,
        edge=0.15,
    )

    # Open position
    store.upsert_position(
        market_id="pnl-test-001",
        question="PnL test market?",
        side="YES",
        price=0.50,
        size=10.0,
    )

    # Close at known price — realized PnL = (0.80 - 0.50) * 10 = 3.0
    store.close_position("pnl-test-001", exit_price=0.80)

    stats = store.get_strategy_stats()
    assert stats["total_trades"] >= 1
    # Should use realized PnL (3.0), not edge-estimated (0.15 * 5.0 = 0.75)
    assert abs(stats["total_pnl"] - 3.0) < 1e-6, f"Expected ~3.0, got {stats['total_pnl']}"
    assert stats["win_rate"] == 1.0, f"Expected 1.0 win_rate, got {stats['win_rate']}"
    assert "avg_edge" in stats

    store.close()
    print("✓ pnl_from_resolved_positions OK")


def test_trader_paper():
    from data_store import DataStore
    from trader import Trader
    from strategy import TradeSignal
    from market_discovery import Market

    store = DataStore()
    trader = Trader(store)
    assert trader.paper_mode is True

    market = Market(
        id="test-456",
        condition_id="cond-456",
        question="Test market?",
        description="A test",
        yes_token_id="token-yes-456",
        no_token_id="token-no-456",
        yes_price=0.60,
        no_price=0.40,
        volume_24h=10000,
        liquidity=5000,
        end_date="2026-12-31",
        category="Test",
        active=True,
        closed=False,
    )

    signal = TradeSignal(
        market_id="test-456",
        question="Test market?",
        side="YES",
        token_id="",
        price=0.60,
        size=5.0,
        cost_usdc=3.0,
        edge=0.10,
        kelly_raw=0.20,
        kelly_adjusted=0.05,
        confidence=0.7,
        reasoning="Test trade",
    )

    result = trader.execute_signal(signal, market)
    assert result.success
    assert result.is_paper
    assert result.order_id.startswith("paper-")

    store.close()
    print("✓ trader paper mode OK")


if __name__ == "__main__":
    test_config()
    test_data_store()
    test_strategy_stats_empty()
    test_pnl_from_resolved_positions()
    test_market_discovery()
    test_strategy()
    test_portfolio()
    test_trader_paper()
    print("\n✓ All tests passed!")
