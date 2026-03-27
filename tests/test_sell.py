"""Tests for sell functionality -- db.reduce_position and trading sell functions."""

import re
from unittest.mock import patch, MagicMock

import pytest

from lib.db import DataStore
from lib.trading import execute_paper_sell


# --- reduce_position tests (use real DB via conftest store fixture) ---


def test_reduce_position_full(store):
    """Full sell closes the position and calculates correct PnL."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )

    pnl = store.reduce_position("mkt1", sell_size=10.0, sell_price=0.80)

    # PnL = (0.80 - 0.60) * 10.0 = 2.0
    assert abs(pnl - 2.0) < 0.001

    # Position should be closed
    open_positions = store.get_open_positions()
    assert len(open_positions) == 0

    closed = store.get_all_closed_positions()
    assert len(closed) == 1
    assert closed[0]["status"] == "closed"
    assert abs(closed[0]["realized_pnl"] - 2.0) < 0.001


def test_reduce_position_partial(store):
    """Partial sell reduces size but keeps position open."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )

    pnl = store.reduce_position("mkt1", sell_size=4.0, sell_price=0.75)

    # PnL = (0.75 - 0.60) * 4.0 = 0.60
    assert abs(pnl - 0.60) < 0.001

    # Position still open with reduced size
    open_positions = store.get_open_positions()
    assert len(open_positions) == 1
    pos = open_positions[0]
    assert abs(pos["size"] - 6.0) < 0.001
    assert abs(pos["avg_price"] - 0.60) < 0.001  # avg_price unchanged
    assert abs(pos["cost_basis"] - 3.60) < 0.001  # 0.60 * 6.0


def test_reduce_position_loss(store):
    """Selling at a loss returns negative PnL."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.70, size=10.0, token_id="tok1",
    )

    pnl = store.reduce_position("mkt1", sell_size=10.0, sell_price=0.50)

    # PnL = (0.50 - 0.70) * 10.0 = -2.0
    assert abs(pnl - (-2.0)) < 0.001


def test_sell_nonexistent_position_fails(store):
    """Selling a position that doesn't exist raises ValueError."""
    with pytest.raises(ValueError, match="No open position"):
        store.reduce_position("nonexistent", sell_size=5.0, sell_price=0.50)


def test_sell_exceeds_held_size_fails(store):
    """Selling more than held size raises ValueError."""
    store.upsert_position(
        market_id="mkt1", question="Will X happen?",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )

    with pytest.raises(ValueError, match="exceeds held size"):
        store.reduce_position("mkt1", sell_size=15.0, sell_price=0.70)


# --- execute_paper_sell tests ---


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_sell_records_action_sell(mock_fill_price, mock_api_fee):
    """Paper sell records trade with action='SELL' and reduces position with fee-adjusted price."""
    mock_fill_price.return_value = 0.75
    mock_api_fee.return_value = None  # fall back to category
    store = MagicMock()
    store.reduce_position.return_value = 1.50  # realized PnL

    result = execute_paper_sell(
        market_id="mkt-1",
        question="Will X happen?",
        side="YES",
        token_id="tok-yes",
        size=10.0,
        host="https://clob.polymarket.com",
        store=store,
        category="other",
    )

    assert result.success is True
    assert result.is_paper is True
    assert "1.50" in result.message

    # Verify fill price came from SELL side (best bid)
    mock_fill_price.assert_called_once_with("tok-yes", "SELL", "https://clob.polymarket.com")

    # Verify reduce_position was called with fee-adjusted effective price (< fill price)
    reduce_call = store.reduce_position.call_args
    effective_sell_price = reduce_call[0][2]
    assert effective_sell_price < 0.75  # fee subtracted
    assert reduce_call[0][0] == "mkt-1"
    assert reduce_call[0][1] == 10.0

    # Verify record_trade was called with action="SELL" and actual fill price
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["action"] == "SELL"
    assert trade_call.kwargs["price"] == 0.75
    assert trade_call.kwargs["fee_amount"] > 0


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_sell_order_id_format(mock_fill_price, mock_api_fee):
    """Paper sell order ID matches format: paper-sell-{12 hex chars}."""
    mock_fill_price.return_value = 0.60
    mock_api_fee.return_value = None
    store = MagicMock()
    store.reduce_position.return_value = 0.0

    result = execute_paper_sell(
        market_id="mkt-2",
        question="Sell test",
        side="NO",
        token_id="tok-no",
        size=20.0,
        host="https://clob.polymarket.com",
        store=store,
    )

    assert result.success is True
    assert re.match(r"^paper-sell-[0-9a-f]{12}$", result.order_id)


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_sell_below_minimum(mock_fill_price, mock_api_fee):
    """Paper sell with notional below minimum returns failed OrderResult."""
    mock_fill_price.return_value = 0.10
    mock_api_fee.return_value = None
    store = MagicMock()

    result = execute_paper_sell(
        market_id="mkt-3",
        question="Below minimum sell",
        side="YES",
        token_id="tok-yes",
        size=2.0,  # notional = 0.10 * 2.0 = 0.20 < 5.0
        host="https://clob.polymarket.com",
        store=store,
    )

    assert result.success is False
    assert "below minimum" in result.message
    store.reduce_position.assert_not_called()


# --- get_closed_positions_since tests ---


def test_get_closed_positions_since(store):
    """get_closed_positions_since returns only positions closed after timestamp."""
    store.upsert_position(
        market_id="mkt1", question="Q1",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    store.upsert_position(
        market_id="mkt2", question="Q2",
        side="NO", price=0.40, size=10.0, token_id="tok2",
    )
    store.reduce_position("mkt1", 10.0, 0.80)

    # Get a timestamp after first close
    closed = store.get_all_closed_positions()
    after_first = closed[0]["closed_at"]

    store.reduce_position("mkt2", 10.0, 0.30)

    # Only mkt2 should appear when filtering since after_first
    recent = store.get_closed_positions_since(after_first)
    market_ids = [p["market_id"] for p in recent]
    assert "mkt2" in market_ids


def test_get_all_closed_positions(store):
    """get_all_closed_positions returns all closed positions."""
    store.upsert_position(
        market_id="mkt1", question="Q1",
        side="YES", price=0.60, size=10.0, token_id="tok1",
    )
    store.upsert_position(
        market_id="mkt2", question="Q2",
        side="NO", price=0.40, size=10.0, token_id="tok2",
    )
    store.reduce_position("mkt1", 10.0, 0.80)
    store.reduce_position("mkt2", 10.0, 0.30)

    closed = store.get_all_closed_positions()
    assert len(closed) == 2


# --- action column migration test ---


def test_action_column_exists(store):
    """Trades table has 'action' column after DataStore init."""
    store.record_trade(
        market_id="mkt1", question="Q1", side="YES",
        price=0.50, size=10.0, action="SELL",
    )
    history = store.get_trade_history()
    assert history[0]["action"] == "SELL"


def test_action_column_default_buy(store):
    """Default action is 'BUY' when not specified."""
    store.record_trade(
        market_id="mkt1", question="Q1", side="YES",
        price=0.50, size=10.0,
    )
    history = store.get_trade_history()
    assert history[0]["action"] == "BUY"
