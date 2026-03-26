"""Tests for lib/market_data.py -- Gamma API market parsing and filtering."""

import json
from unittest.mock import patch, MagicMock

import pytest

from lib.market_data import _parse_market, _passes_filters, fetch_active_markets
from lib.models import Market


# --- Helpers ---

def _make_raw_market(**overrides) -> dict:
    """Create a raw Gamma API market dict with sensible defaults."""
    base = {
        "id": "12345",
        "conditionId": "0xcondition123",
        "question": "Will X happen?",
        "description": "A test market about X.",
        "clobTokenIds": json.dumps(["token_yes_1", "token_no_1"]),
        "outcomePrices": json.dumps(["0.65", "0.35"]),
        "bestBid": "0.60",
        "bestAsk": "0.70",
        "volume24hr": "50000",
        "liquidityNum": "10000",
        "endDate": "2026-12-31T00:00:00Z",
        "groupItemTitle": "Politics",
        "active": True,
        "closed": False,
        "negRisk": False,
        "orderMinSize": "5",
        "orderPriceMinTickSize": "0.01",
    }
    base.update(overrides)
    return base


def _make_market(**overrides) -> Market:
    """Create a Market dataclass with sensible defaults."""
    defaults = {
        "id": "12345",
        "condition_id": "0xcondition123",
        "question": "Will X happen?",
        "description": "A test market about X.",
        "yes_token_id": "token_yes_1",
        "no_token_id": "token_no_1",
        "yes_price": 0.65,
        "no_price": 0.35,
        "best_bid": 0.60,
        "best_ask": 0.70,
        "volume_24h": 50000.0,
        "liquidity": 10000.0,
        "end_date": "2026-12-31T00:00:00Z",
        "category": "Politics",
        "active": True,
        "closed": False,
        "neg_risk": False,
        "order_min_size": 5.0,
        "tick_size": 0.01,
    }
    defaults.update(overrides)
    return Market(**defaults)


# --- _parse_market tests ---

def test_parse_market_valid():
    """Parse a complete raw market dict into a Market dataclass."""
    raw = _make_raw_market()
    market = _parse_market(raw)

    assert market is not None
    assert market.id == "12345"
    assert market.condition_id == "0xcondition123"
    assert market.question == "Will X happen?"
    assert market.yes_token_id == "token_yes_1"
    assert market.no_token_id == "token_no_1"
    assert market.yes_price == 0.65
    assert market.no_price == 0.35
    assert market.best_bid == 0.60
    assert market.best_ask == 0.70
    assert market.volume_24h == 50000.0
    assert market.liquidity == 10000.0
    assert market.active is True
    assert market.closed is False
    assert market.neg_risk is False
    assert market.order_min_size == 5.0
    assert market.tick_size == 0.01


def test_parse_market_stringified_json():
    """clobTokenIds and outcomePrices arrive as JSON strings, not lists."""
    raw = _make_raw_market(
        clobTokenIds='["token_a","token_b"]',
        outcomePrices='["0.72","0.28"]',
    )
    market = _parse_market(raw)

    assert market is not None
    assert market.yes_token_id == "token_a"
    assert market.no_token_id == "token_b"
    assert market.yes_price == 0.72
    assert market.no_price == 0.28


def test_parse_market_native_list():
    """clobTokenIds as native list (not stringified) also works."""
    raw = _make_raw_market(
        clobTokenIds=["tok_yes", "tok_no"],
        outcomePrices=["0.50", "0.50"],
    )
    market = _parse_market(raw)

    assert market is not None
    assert market.yes_token_id == "tok_yes"
    assert market.no_token_id == "tok_no"


def test_parse_market_missing_tokens():
    """Return None when clobTokenIds is missing."""
    raw = _make_raw_market()
    del raw["clobTokenIds"]
    market = _parse_market(raw)

    assert market is None


def test_parse_market_single_token():
    """Return None when clobTokenIds has fewer than 2 tokens."""
    raw = _make_raw_market(clobTokenIds=json.dumps(["only_one"]))
    market = _parse_market(raw)

    assert market is None


def test_neg_risk_detection():
    """Neg-risk markets are detected via the negRisk field (INST-09)."""
    raw = _make_raw_market(negRisk=True)
    market = _parse_market(raw)

    assert market is not None
    assert market.neg_risk is True


def test_parse_market_snake_case_fields():
    """Handle snake_case field names (alternative API format)."""
    raw = {
        "id": "99",
        "condition_id": "0xabc",
        "question": "Snake case?",
        "description": "",
        "clob_token_ids": json.dumps(["t1", "t2"]),
        "outcome_prices": json.dumps(["0.40", "0.60"]),
        "bestBid": "0.38",
        "bestAsk": "0.42",
        "volume_num_24hr": "2000",
        "liquidity_num": "800",
        "end_date_iso": "2026-06-01",
        "category": "Sports",
        "active": True,
        "closed": False,
        "negRisk": False,
        "orderMinSize": "5",
        "orderPriceMinTickSize": "0.01",
    }
    market = _parse_market(raw)

    assert market is not None
    assert market.condition_id == "0xabc"
    assert market.yes_token_id == "t1"
    assert market.yes_price == 0.40
    assert market.volume_24h == 2000.0
    assert market.liquidity == 800.0


# --- _passes_filters tests ---

def test_passes_filters_valid():
    """Market with good values passes all filters."""
    market = _make_market()
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is True


def test_passes_filters_low_volume():
    """Market with low volume is rejected."""
    market = _make_market(volume_24h=10.0)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_low_liquidity():
    """Market with low liquidity is rejected."""
    market = _make_market(liquidity=100.0)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_extreme_price_high():
    """Market with yes_price > 0.95 is rejected."""
    market = _make_market(yes_price=0.99)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_extreme_price_low():
    """Market with yes_price < 0.05 is rejected."""
    market = _make_market(yes_price=0.02)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_closed():
    """Closed market is rejected."""
    market = _make_market(closed=True)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_inactive():
    """Inactive market is rejected."""
    market = _make_market(active=False)
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


def test_passes_filters_missing_token():
    """Market with empty token ID is rejected."""
    market = _make_market(yes_token_id="")
    assert _passes_filters(market, min_volume=1000, min_liquidity=500) is False


# --- fetch_active_markets tests (mocked HTTP) ---

@patch("lib.market_data.requests.get")
def test_fetch_active_markets_returns_markets(mock_get):
    """fetch_active_markets returns parsed and filtered Market objects."""
    raw_markets = [
        _make_raw_market(id="1", question="Market 1"),
        _make_raw_market(id="2", question="Market 2"),
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = raw_markets
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    markets = fetch_active_markets(
        gamma_api_url="https://gamma-api.polymarket.com",
        min_volume=1000,
        min_liquidity=500,
        limit=10,
    )

    assert len(markets) == 2
    assert all(isinstance(m, Market) for m in markets)
    assert markets[0].id == "1"
    assert markets[1].id == "2"


@patch("lib.market_data.requests.get")
def test_fetch_active_markets_api_error(mock_get):
    """fetch_active_markets returns empty list on API error (safe default)."""
    mock_get.side_effect = Exception("Connection refused")

    markets = fetch_active_markets(
        gamma_api_url="https://gamma-api.polymarket.com",
    )

    assert markets == []


@patch("lib.market_data.requests.get")
def test_fetch_active_markets_respects_limit(mock_get):
    """fetch_active_markets slices result to requested limit."""
    raw_markets = [_make_raw_market(id=str(i)) for i in range(20)]
    mock_response = MagicMock()
    mock_response.json.return_value = raw_markets
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    markets = fetch_active_markets(
        gamma_api_url="https://gamma-api.polymarket.com",
        min_volume=0,
        min_liquidity=0,
        limit=3,
    )

    assert len(markets) == 3


# --- Integration test (marked, requires network) ---

@pytest.mark.integration
def test_fetch_active_markets_integration():
    """Integration test: call live Gamma API with limit=2."""
    markets = fetch_active_markets(
        gamma_api_url="https://gamma-api.polymarket.com",
        min_volume=0,
        min_liquidity=0,
        limit=2,
    )

    assert isinstance(markets, list)
    for m in markets:
        assert isinstance(m, Market)
        assert hasattr(m, "neg_risk")
        assert isinstance(m.neg_risk, bool)
