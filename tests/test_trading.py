"""Tests for lib/trading.py -- paper and live trade execution."""

import re
from unittest.mock import patch, MagicMock, call

import pytest
from py_clob_client.clob_types import OrderType

from lib.trading import validate_order, execute_paper_trade, execute_live_trade
from lib.models import OrderResult


# --- validate_order tests ---


def test_validate_order_valid():
    """Valid order: notional 10.0 >= 5.0 minimum."""
    valid, msg = validate_order(0.50, 20.0, 5.0)
    assert valid is True
    assert msg == ""


def test_validate_order_minimum():
    """Order notional 0.20 below 5 USDC minimum."""
    valid, msg = validate_order(0.10, 2.0, 5.0)
    assert valid is False
    assert "below minimum" in msg


def test_validate_order_price_too_low():
    """Price 0 is invalid (must be > 0)."""
    valid, msg = validate_order(0.0, 20.0, 5.0)
    assert valid is False
    assert "between 0 and 1" in msg


def test_validate_order_price_too_high():
    """Price 1.0 is invalid (must be < 1)."""
    valid, msg = validate_order(1.0, 20.0, 5.0)
    assert valid is False
    assert "between 0 and 1" in msg


def test_validate_order_negative_price():
    """Negative price is invalid."""
    valid, msg = validate_order(-0.5, 20.0, 5.0)
    assert valid is False
    assert "between 0 and 1" in msg


def test_validate_order_size_rounded():
    """Size with >2 decimals gets rounded; notional still checked after rounding."""
    # 0.50 * round(10.123, 2) = 0.50 * 10.12 = 5.06 >= 5.0 -> valid
    valid, msg = validate_order(0.50, 10.123, 5.0)
    assert valid is True
    assert msg == ""


# --- execute_paper_trade tests ---


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_fill_pricing(mock_fill_price, mock_api_fee):
    """Paper trade uses fill price from CLOB API (best ask for buys)."""
    mock_fill_price.return_value = 0.65
    mock_api_fee.return_value = None
    store = MagicMock()

    result = execute_paper_trade(
        market_id="mkt-1",
        question="Will X happen?",
        side="YES",
        token_id="tok-yes",
        size=20.0,
        host="https://clob.polymarket.com",
        store=store,
    )

    assert result.success is True
    assert result.is_paper is True
    mock_fill_price.assert_called_once_with("tok-yes", "BUY", "https://clob.polymarket.com")

    # Verify the recorded trade price is the fill price (0.65)
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["price"] == 0.65
    assert trade_call.kwargs["fill_price"] == 0.65
    assert trade_call.kwargs["fee_amount"] >= 0


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_records_to_db(mock_fill_price, mock_api_fee):
    """Paper trade records to database (record_trade and upsert_position)."""
    mock_fill_price.return_value = 0.55
    mock_api_fee.return_value = None
    store = MagicMock()

    execute_paper_trade(
        market_id="mkt-2",
        question="Test market",
        side="NO",
        token_id="tok-no",
        size=15.0,
        host="https://clob.polymarket.com",
        store=store,
    )

    store.record_trade.assert_called_once()
    store.upsert_position.assert_called_once()


@patch("lib.trading.get_fill_price")
def test_paper_trade_fails_on_no_liquidity(mock_fill_price):
    """Paper trade fails when CLOB API is unreachable (D-10: no fake fills)."""
    mock_fill_price.side_effect = ValueError("No liquidity for BUY on token tok-1")
    store = MagicMock()

    with pytest.raises(ValueError, match="No liquidity"):
        execute_paper_trade(
            market_id="mkt-3",
            question="No liquidity market",
            side="YES",
            token_id="tok-1",
            size=10.0,
            host="https://clob.polymarket.com",
            store=store,
        )


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_order_id_format(mock_fill_price, mock_api_fee):
    """Paper trade order ID matches format: paper-{12 hex chars}."""
    mock_fill_price.return_value = 0.50
    mock_api_fee.return_value = None
    store = MagicMock()

    result = execute_paper_trade(
        market_id="mkt-4",
        question="Order ID test",
        side="YES",
        token_id="tok-yes",
        size=20.0,
        host="https://clob.polymarket.com",
        store=store,
    )

    assert result.success is True
    assert re.match(r"^paper-[0-9a-f]{12}$", result.order_id)


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_uses_effective_price_for_position(mock_fill_price, mock_api_fee):
    """upsert_position is called with fee-adjusted effective price (> fill price)."""
    mock_fill_price.return_value = 0.65
    mock_api_fee.return_value = None
    store = MagicMock()

    execute_paper_trade(
        market_id="mkt-5",
        question="Position price test",
        side="YES",
        token_id="tok-yes",
        size=20.0,
        host="https://clob.polymarket.com",
        store=store,
        category="other",
    )

    pos_call = store.upsert_position.call_args
    # Effective price should be higher than fill price due to entry fee
    assert pos_call.kwargs["price"] > 0.65

    # Trade record should still use actual fill price
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["price"] == 0.65


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_below_minimum(mock_fill_price, mock_api_fee):
    """Paper trade with notional below minimum returns failed OrderResult."""
    mock_fill_price.return_value = 0.10
    mock_api_fee.return_value = None
    store = MagicMock()

    result = execute_paper_trade(
        market_id="mkt-6",
        question="Below minimum",
        side="YES",
        token_id="tok-yes",
        size=2.0,  # notional = 0.10 * 2.0 = 0.20 < 5.0
        host="https://clob.polymarket.com",
        store=store,
    )

    assert result.success is False
    assert "below minimum" in result.message
    store.record_trade.assert_not_called()


# --- execute_live_trade tests ---


@patch("lib.trading.ClobClient")
def test_live_trade_creates_gtc_order(mock_clob_cls):
    """Live trade creates a signed GTC limit order with BUY side."""
    mock_client = MagicMock()
    mock_clob_cls.return_value = mock_client
    mock_client.create_or_derive_api_creds.return_value = {"apiKey": "k", "secret": "s", "passphrase": "p"}
    mock_client.create_order.return_value = {"signed": True}
    mock_client.post_order.return_value = {"orderID": "live-order-1", "success": True}
    store = MagicMock()

    result = execute_live_trade(
        market_id="mkt-live-1",
        question="Live trade test",
        side="YES",
        token_id="tok-yes",
        price=0.55,
        size=20.0,
        host="https://clob.polymarket.com",
        private_key="0xdeadbeef",
        chain_id=137,
        store=store,
    )

    assert result.success is True
    assert result.order_id == "live-order-1"
    assert result.is_paper is False

    # Verify create_order was called with BUY side
    create_call = mock_client.create_order.call_args
    order_args = create_call[0][0]
    assert order_args.side == "BUY"

    # Verify post_order was called with GTC
    post_call = mock_client.post_order.call_args
    assert post_call[0][1] == OrderType.GTC


@patch("lib.trading.ClobClient")
def test_live_trade_signature_type_zero(mock_clob_cls):
    """ClobClient instantiated with signature_type=0 for EOA wallets."""
    mock_client = MagicMock()
    mock_clob_cls.return_value = mock_client
    mock_client.create_or_derive_api_creds.return_value = {"apiKey": "k", "secret": "s", "passphrase": "p"}
    mock_client.create_order.return_value = {"signed": True}
    mock_client.post_order.return_value = {"orderID": "live-2"}
    store = MagicMock()

    execute_live_trade(
        market_id="mkt-live-2",
        question="Sig type test",
        side="NO",
        token_id="tok-no",
        price=0.40,
        size=30.0,
        host="https://clob.polymarket.com",
        private_key="0xkey123",
        chain_id=137,
        store=store,
    )

    # Verify ClobClient was created with signature_type=0
    init_call = mock_clob_cls.call_args
    assert init_call.kwargs.get("signature_type") == 0 or init_call[1].get("signature_type") == 0


@patch("lib.trading.ClobClient")
def test_live_trade_fails_gracefully(mock_clob_cls):
    """Live trade returns failed OrderResult on exception."""
    mock_client = MagicMock()
    mock_clob_cls.return_value = mock_client
    mock_client.create_or_derive_api_creds.return_value = {"apiKey": "k", "secret": "s", "passphrase": "p"}
    mock_client.create_order.side_effect = Exception("Network error")
    store = MagicMock()

    result = execute_live_trade(
        market_id="mkt-fail",
        question="Failing trade",
        side="YES",
        token_id="tok-yes",
        price=0.60,
        size=20.0,
        host="https://clob.polymarket.com",
        private_key="0xdeadbeef",
        chain_id=137,
        store=store,
    )

    assert result.success is False
    assert "Network error" in result.message
    assert result.is_paper is False
    store.record_trade.assert_not_called()


@patch("lib.trading.ClobClient")
def test_live_trade_records_to_db(mock_clob_cls):
    """Live trade records to database on success."""
    mock_client = MagicMock()
    mock_clob_cls.return_value = mock_client
    mock_client.create_or_derive_api_creds.return_value = {"apiKey": "k", "secret": "s", "passphrase": "p"}
    mock_client.create_order.return_value = {"signed": True}
    mock_client.post_order.return_value = {"orderID": "live-3"}
    store = MagicMock()

    result = execute_live_trade(
        market_id="mkt-live-3",
        question="DB record test",
        side="YES",
        token_id="tok-yes",
        price=0.50,
        size=20.0,
        host="https://clob.polymarket.com",
        private_key="0xkey",
        chain_id=137,
        store=store,
    )

    assert result.success is True
    store.record_trade.assert_called_once()
    store.upsert_position.assert_called_once()

    # Verify is_paper=False in record_trade
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["is_paper"] is False
