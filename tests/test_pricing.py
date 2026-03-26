"""Tests for lib/pricing.py -- CLOB API pricing with correct side semantics."""

from unittest.mock import patch, MagicMock

import pytest

from lib.pricing import get_fill_price, get_best_bid, get_best_ask


FAKE_HOST = "https://clob.polymarket.com"
FAKE_TOKEN = "token_abc_123"


@patch("lib.pricing.ClobClient")
def test_get_fill_price_buy(mock_clob_cls):
    """BUY fill price should return the best ask (from SELL side of book)."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.65"}
    mock_clob_cls.return_value = mock_client

    price = get_fill_price(FAKE_TOKEN, "BUY", FAKE_HOST)

    assert price == 0.65


@patch("lib.pricing.ClobClient")
def test_get_fill_price_sell(mock_clob_cls):
    """SELL fill price should return the best bid (from BUY side of book)."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.55"}
    mock_clob_cls.return_value = mock_client

    price = get_fill_price(FAKE_TOKEN, "SELL", FAKE_HOST)

    assert price == 0.55


@patch("lib.pricing.ClobClient")
def test_get_fill_price_no_liquidity(mock_clob_cls):
    """Raise ValueError when price is 0 (no liquidity)."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0"}
    mock_clob_cls.return_value = mock_client

    with pytest.raises(ValueError, match="No liquidity"):
        get_fill_price(FAKE_TOKEN, "BUY", FAKE_HOST)


@patch("lib.pricing.ClobClient")
def test_get_best_bid(mock_clob_cls):
    """get_best_bid calls get_price with BUY side."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.55"}
    mock_clob_cls.return_value = mock_client

    price = get_best_bid(FAKE_TOKEN, FAKE_HOST)

    assert price == 0.55
    mock_client.get_price.assert_called_once_with(FAKE_TOKEN, "BUY")


@patch("lib.pricing.ClobClient")
def test_get_best_ask(mock_clob_cls):
    """get_best_ask calls get_price with SELL side."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.65"}
    mock_clob_cls.return_value = mock_client

    price = get_best_ask(FAKE_TOKEN, FAKE_HOST)

    assert price == 0.65
    mock_client.get_price.assert_called_once_with(FAKE_TOKEN, "SELL")


@patch("lib.pricing.ClobClient")
def test_buy_uses_sell_side(mock_clob_cls):
    """Verify BUY calls get_price with 'SELL' (inverted semantics)."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.70"}
    mock_clob_cls.return_value = mock_client

    get_fill_price(FAKE_TOKEN, "BUY", FAKE_HOST)

    # BUY should query the SELL side of the book to get best ask
    mock_client.get_price.assert_called_once_with(FAKE_TOKEN, "SELL")


@patch("lib.pricing.ClobClient")
def test_sell_uses_buy_side(mock_clob_cls):
    """Verify SELL calls get_price with 'BUY' (inverted semantics)."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0.50"}
    mock_clob_cls.return_value = mock_client

    get_fill_price(FAKE_TOKEN, "SELL", FAKE_HOST)

    # SELL should query the BUY side of the book to get best bid
    mock_client.get_price.assert_called_once_with(FAKE_TOKEN, "BUY")


@patch("lib.pricing.ClobClient")
def test_get_fill_price_invalid_side(mock_clob_cls):
    """Raise ValueError for invalid trade_side."""
    with pytest.raises(ValueError, match="Invalid trade side"):
        get_fill_price(FAKE_TOKEN, "INVALID", FAKE_HOST)


@patch("lib.pricing.ClobClient")
def test_get_best_bid_no_liquidity(mock_clob_cls):
    """get_best_bid raises ValueError when no bids."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0"}
    mock_clob_cls.return_value = mock_client

    with pytest.raises(ValueError, match="No bid liquidity"):
        get_best_bid(FAKE_TOKEN, FAKE_HOST)


@patch("lib.pricing.ClobClient")
def test_get_best_ask_no_liquidity(mock_clob_cls):
    """get_best_ask raises ValueError when no asks."""
    mock_client = MagicMock()
    mock_client.get_price.return_value = {"price": "0"}
    mock_clob_cls.return_value = mock_client

    with pytest.raises(ValueError, match="No ask liquidity"):
        get_best_ask(FAKE_TOKEN, FAKE_HOST)
