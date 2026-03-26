from lib.db import DataStore


def test_tables_created(store):
    """All 5 tables exist after DataStore init."""
    rows = store.conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = sorted([
        r["name"] for r in rows
        if not r["name"].startswith("sqlite_")
    ])
    expected = sorted(["trades", "positions", "decisions", "market_snapshots", "strategy_metrics"])
    assert table_names == expected


def test_record_trade(store):
    """record_trade returns int > 0 and trade appears in history."""
    trade_id = store.record_trade(
        market_id="mkt1", question="Will X happen?", side="YES",
        price=0.60, size=10.0, token_id="tok1", condition_id="cond1",
        order_id="ord1", is_paper=True, estimated_prob=0.7,
        edge=0.10, reasoning="Test trade",
    )
    assert isinstance(trade_id, int)
    assert trade_id > 0

    history = store.get_trade_history()
    assert len(history) == 1
    assert history[0]["market_id"] == "mkt1"
    assert history[0]["side"] == "YES"
    assert history[0]["cost_usdc"] == 6.0  # 0.60 * 10


def test_upsert_position_new(store):
    """Upserting a new market creates one open position."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    positions = store.get_open_positions()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["market_id"] == "mkt1"
    assert pos["side"] == "YES"
    assert pos["avg_price"] == 0.60
    assert pos["size"] == 10.0
    assert pos["cost_basis"] == 6.0


def test_upsert_position_existing(store):
    """Upserting same market_id sums size and recalculates avg price."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.80, size=10.0, token_id="tok1",
    )
    positions = store.get_open_positions()
    assert len(positions) == 1
    pos = positions[0]
    assert pos["size"] == 20.0
    # cost_basis = 6.0 + 8.0 = 14.0, avg_price = 14.0 / 20.0 = 0.70
    assert pos["cost_basis"] == 14.0
    assert pos["avg_price"] == 0.70


def test_close_position(store):
    """Closing a position marks it closed with correct realized PnL."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    store.close_position("mkt1", exit_price=0.80)

    # No more open positions
    open_positions = store.get_open_positions()
    assert len(open_positions) == 0

    # Check realized PnL = (0.80 - 0.60) * 10.0 = 2.0
    closed = store.conn.execute(
        "SELECT * FROM positions WHERE market_id = 'mkt1'"
    ).fetchone()
    assert closed["status"] == "closed"
    assert abs(closed["realized_pnl"] - 2.0) < 0.001


def test_get_total_exposure(store):
    """Total exposure equals sum of cost_basis for open positions."""
    store.upsert_position(
        market_id="mkt1", question="Q1",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    store.upsert_position(
        market_id="mkt2", question="Q2",
        side="NO", price=0.40, size=20.0, token_id="tok2",
    )
    total = store.get_total_exposure()
    # 0.60*10 + 0.40*20 = 6.0 + 8.0 = 14.0
    assert abs(total - 14.0) < 0.001


def test_get_strategy_stats_empty(store):
    """Empty store returns total_trades: 0."""
    stats = store.get_strategy_stats()
    assert stats["total_trades"] == 0
    assert stats["win_rate"] == 0
    assert stats["total_pnl"] == 0
    assert stats["avg_edge"] == 0


def test_get_strategy_stats_with_trades(store):
    """Strategy stats computed from trades and closed positions."""
    # Record two trades
    store.record_trade(
        market_id="mkt1", question="Q1", side="YES",
        price=0.50, size=10.0, edge=0.10,
    )
    store.record_trade(
        market_id="mkt2", question="Q2", side="NO",
        price=0.40, size=10.0, edge=0.05,
    )

    # Open and close positions to get realized PnL
    store.upsert_position(
        market_id="mkt1", question="Q1",
        side="YES", price=0.50, size=10.0,
    )
    store.upsert_position(
        market_id="mkt2", question="Q2",
        side="NO", price=0.40, size=10.0,
    )
    store.close_position("mkt1", exit_price=0.70)  # PnL = (0.70-0.50)*10 = 2.0
    store.close_position("mkt2", exit_price=0.30)  # PnL = (0.30-0.40)*10 = -1.0

    stats = store.get_strategy_stats()
    assert stats["total_trades"] == 2
    assert stats["avg_edge"] == (0.10 + 0.05) / 2
    assert abs(stats["total_pnl"] - 1.0) < 0.001  # 2.0 + (-1.0) = 1.0
    assert stats["win_rate"] == 0.5  # 1 win out of 2


def test_record_trade_with_neg_risk(store):
    """Trade with neg_risk=True is stored correctly."""
    trade_id = store.record_trade(
        market_id="mkt_neg", question="Neg risk question?", side="YES",
        price=0.55, size=5.0, neg_risk=True, fill_price=0.56,
    )
    assert trade_id > 0

    history = store.get_trade_history()
    trade = history[0]
    assert trade["neg_risk"] == 1
    assert trade["fill_price"] == 0.56
