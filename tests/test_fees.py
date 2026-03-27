"""Tests for lib/fees.py -- Polymarket fee calculation and integration."""

import logging
from unittest.mock import patch, MagicMock

import pytest

from lib.fees import (
    FEE_PARAMS,
    calculate_fee,
    calculate_fee_per_share,
    estimate_round_trip_fee_rate,
    get_fee_rate_from_api,
)


# --- Fee formula tests ---


def test_fee_formula_crypto_at_50pct():
    """100 shares at $0.50 crypto -> fee = $0.90 (1.80% of $50 notional)."""
    fee = calculate_fee(100, 0.50, "crypto")
    assert abs(fee - 0.90) < 0.0001


def test_fee_lower_at_extremes_than_midrange():
    """Fee at extreme prices is lower than at p=0.50."""
    fee_mid = calculate_fee(100, 0.50, "crypto")
    fee_low = calculate_fee(100, 0.05, "crypto")
    fee_high = calculate_fee(100, 0.95, "crypto")
    # Extreme prices should produce smaller fees than midrange
    assert fee_low < fee_mid
    assert fee_high < fee_mid
    # At p=0.50 the prob_factor (p*(1-p)) is maximized at 0.25
    # At p=0.05 it's 0.0475, at p=0.95 it's 0.0475
    # So fee should be significantly less
    assert fee_low < fee_mid * 0.5
    assert fee_high < fee_mid * 0.5


def test_fee_rate_peaks_at_50pct():
    """Fee RATE (fee/notional) peaks at p=0.50 for all categories.

    Note: total fee amount peaks at p=2/3 for exp=1 due to the extra `price`
    multiplier, but the fee rate as fraction of notional peaks at 0.50.
    """
    for cat in ["crypto", "sports", "finance", "politics", "culture", "tech"]:
        # Fee rate = fee / (shares * price) = fee_rate_param * (p*(1-p))^exp
        rate_at_50 = calculate_fee(100, 0.50, cat) / (100 * 0.50)
        rate_at_30 = calculate_fee(100, 0.30, cat) / (100 * 0.30)
        rate_at_70 = calculate_fee(100, 0.70, cat) / (100 * 0.70)
        assert rate_at_50 >= rate_at_30, f"{cat}: rate at 0.50 should >= rate at 0.30"
        assert rate_at_50 >= rate_at_70, f"{cat}: rate at 0.50 should >= rate at 0.70"


def test_fee_by_category_peak_rates():
    """Verify each category's peak rate (at p=0.50) matches documented values."""
    # At p=0.50: fee = shares * 0.50 * fee_rate * (0.50 * 0.50)^exp
    # For exp=1: fee = shares * 0.50 * fee_rate * 0.25 = shares * fee_rate * 0.125
    # Peak rate as % of notional (shares*price) = fee_rate * 0.25 for exp=1
    expected_peaks = {
        "crypto": 0.018,      # 0.072 * 0.25 = 0.018 (1.80%)
        "sports": 0.0075,     # 0.03 * 0.25 = 0.0075 (0.75%)
        "finance": 0.01,      # 0.04 * 0.25 = 0.01 (1.00%)
        "politics": 0.01,     # 0.04 * 0.25 = 0.01 (1.00%)
        "culture": 0.0125,    # 0.05 * 0.25 = 0.0125 (1.25%)
        "tech": 0.01,         # 0.04 * 0.25 = 0.01 (1.00%)
    }
    for cat, expected_rate in expected_peaks.items():
        fee = calculate_fee(100, 0.50, cat)
        notional = 100 * 0.50
        actual_rate = fee / notional
        assert abs(actual_rate - expected_rate) < 0.001, (
            f"{cat}: expected peak rate {expected_rate}, got {actual_rate}"
        )


def test_geopolitics_zero():
    """Geopolitics has zero fee (fee_rate=0)."""
    fee = calculate_fee(100, 0.50, "geopolitics")
    assert fee == 0.0


def test_default_category_fallback(caplog):
    """Unknown category uses 'other' with warning logged."""
    with caplog.at_level(logging.WARNING, logger="fees"):
        fee = calculate_fee(100, 0.50, "unknown_category")
    assert fee > 0  # "other" has non-zero fee
    assert "Unknown category" in caplog.text
    assert "defaulting to" in caplog.text


def test_fee_rounding_4_decimals():
    """Fees are rounded to 4 decimal places."""
    # Use a small trade to get a fee with many decimal places
    fee = calculate_fee(1, 0.50, "sports")
    # 1 * 0.50 * 0.03 * 0.25 = 0.00375 -> round to 0.0038
    assert fee == round(fee, 4)
    # Verify it's exactly 4 decimal places
    fee_str = f"{fee:.4f}"
    assert float(fee_str) == fee


def test_fee_below_minimum_rounds_to_zero():
    """Fee < 0.0001 becomes 0."""
    # Very small trade at extreme price
    fee = calculate_fee(0.01, 0.01, "sports")
    # 0.01 * 0.01 * 0.03 * (0.01 * 0.99) = 0.000003 * 0.0099 ≈ 0.00000003
    assert fee == 0.0


# --- calculate_fee_per_share tests ---


def test_fee_per_share_equals_single_share_fee():
    """calculate_fee_per_share matches calculate_fee with shares=1."""
    for cat in ["crypto", "sports", "finance", "other"]:
        for price in [0.20, 0.50, 0.80]:
            per_share = calculate_fee_per_share(price, cat)
            single = calculate_fee(1, price, cat)
            assert per_share == single


# --- estimate_round_trip_fee_rate tests ---


def test_round_trip_fee_estimate():
    """Entry + exit fee is ~2x single-leg fee rate."""
    rate = estimate_round_trip_fee_rate(0.50, "crypto")
    single_fee = calculate_fee_per_share(0.50, "crypto")
    expected = 2 * single_fee / 0.50
    assert abs(rate - expected) < 0.0001


def test_round_trip_fee_at_extremes():
    """Round-trip fee rate is 0 at extreme prices."""
    rate_low = estimate_round_trip_fee_rate(0.0, "crypto")
    rate_high = estimate_round_trip_fee_rate(1.0, "crypto")
    assert rate_low == 0.0
    assert rate_high == 0.0


# --- get_fee_rate_from_api tests ---


@patch("lib.fees.requests.get")
def test_api_fee_rate_success(mock_get):
    """Successful API call returns fee rate as decimal."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"base_fee": 180}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    rate = get_fee_rate_from_api("tok-123", "https://clob.polymarket.com")
    assert rate == 0.018  # 180 bps = 1.80%
    mock_get.assert_called_once_with(
        "https://clob.polymarket.com/fee-rate?token_id=tok-123",
        timeout=5,
    )


@patch("lib.fees.requests.get")
def test_api_fee_rate_network_error(mock_get):
    """Network error returns None (fallback to category)."""
    mock_get.side_effect = Exception("Connection timeout")

    rate = get_fee_rate_from_api("tok-456", "https://clob.polymarket.com")
    assert rate is None


@patch("lib.fees.requests.get")
def test_api_fee_rate_zero_bps(mock_get):
    """API returning 0 bps returns None (use category fallback)."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"base_fee": 0}
    mock_resp.raise_for_status.return_value = None
    mock_get.return_value = mock_resp

    rate = get_fee_rate_from_api("tok-789", "https://clob.polymarket.com")
    assert rate is None


# --- Integration tests: paper trade with fees ---


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_cost_basis_includes_fee(mock_fill, mock_api_fee):
    """Paper buy position uses effective_price > fill_price."""
    from lib.trading import execute_paper_trade

    mock_fill.return_value = 0.50
    mock_api_fee.return_value = None  # fall back to category

    store = MagicMock()

    result = execute_paper_trade(
        market_id="mkt-fee-1",
        question="Fee test market",
        side="YES",
        token_id="tok-yes",
        size=100.0,
        host="https://clob.polymarket.com",
        store=store,
        category="crypto",
    )

    assert result.success is True

    # Check that record_trade used actual fill price
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["price"] == 0.50
    assert trade_call.kwargs["fee_amount"] > 0

    # Check that upsert_position used effective price (> fill price)
    pos_call = store.upsert_position.call_args
    effective_price = pos_call.kwargs["price"]
    assert effective_price > 0.50  # fee added


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_sell_pnl_reduced_by_fee(mock_fill, mock_api_fee):
    """Paper sell uses effective_price < fill_price, reducing realized PnL."""
    from lib.trading import execute_paper_sell

    mock_fill.return_value = 0.60
    mock_api_fee.return_value = None  # fall back to category

    store = MagicMock()
    store.reduce_position.return_value = 1.0  # mock PnL

    result = execute_paper_sell(
        market_id="mkt-fee-2",
        question="Fee sell test",
        side="YES",
        token_id="tok-yes",
        size=100.0,
        host="https://clob.polymarket.com",
        store=store,
        category="crypto",
    )

    assert result.success is True

    # Check that reduce_position was called with effective price < fill price
    reduce_call = store.reduce_position.call_args
    effective_sell_price = reduce_call[0][2]  # 3rd positional arg
    assert effective_sell_price < 0.60  # fee subtracted

    # Check fee_amount recorded
    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["fee_amount"] > 0


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_api_fee_overrides_category(mock_fill, mock_api_fee):
    """When API fee rate is available, it overrides category-based calculation."""
    from lib.trading import execute_paper_trade

    mock_fill.return_value = 0.50
    mock_api_fee.return_value = 0.02  # 200 bps from API

    store = MagicMock()

    execute_paper_trade(
        market_id="mkt-api-fee",
        question="API fee test",
        side="YES",
        token_id="tok-yes",
        size=100.0,
        host="https://clob.polymarket.com",
        store=store,
        category="sports",  # would give different rate, but API overrides
    )

    # API rate: fee_per_share = 0.02 * 0.50 = 0.01
    # fee_amount = 0.02 * 0.50 * 100 = 1.0
    trade_call = store.record_trade.call_args
    assert abs(trade_call.kwargs["fee_amount"] - 1.0) < 0.0001

    pos_call = store.upsert_position.call_args
    assert abs(pos_call.kwargs["price"] - 0.51) < 0.0001  # 0.50 + 0.01


@patch("lib.trading.get_fee_rate_from_api")
@patch("lib.trading.get_fill_price")
def test_paper_trade_geopolitics_zero_fee(mock_fill, mock_api_fee):
    """Geopolitics category results in zero fee — effective price equals fill price."""
    from lib.trading import execute_paper_trade

    mock_fill.return_value = 0.50
    mock_api_fee.return_value = None

    store = MagicMock()

    execute_paper_trade(
        market_id="mkt-geo",
        question="Geopolitics test",
        side="YES",
        token_id="tok-yes",
        size=100.0,
        host="https://clob.polymarket.com",
        store=store,
        category="geopolitics",
    )

    trade_call = store.record_trade.call_args
    assert trade_call.kwargs["fee_amount"] == 0.0

    pos_call = store.upsert_position.call_args
    assert pos_call.kwargs["price"] == 0.50  # no fee adjustment


# --- Strategy fee_adjustment test ---


def test_calculate_edge_with_fee_adjustment():
    """Edge calculation subtracts fee_adjustment."""
    from lib.strategy import calculate_edge

    edge_no_fee = calculate_edge(0.60, 0.50)
    assert abs(edge_no_fee - 0.10) < 0.000001

    edge_with_fee = calculate_edge(0.60, 0.50, fee_adjustment=0.03)
    assert abs(edge_with_fee - 0.07) < 0.000001


# --- DB fee_amount migration test ---


def test_fee_amount_column_exists(store):
    """Trades table has 'fee_amount' column after DataStore init."""
    store.record_trade(
        market_id="mkt1", question="Q1", side="YES",
        price=0.50, size=10.0, fee_amount=0.45,
    )
    history = store.get_trade_history()
    assert history[0]["fee_amount"] == 0.45


def test_fee_amount_default_zero(store):
    """Default fee_amount is 0 when not specified."""
    store.record_trade(
        market_id="mkt1", question="Q1", side="YES",
        price=0.50, size=10.0,
    )
    history = store.get_trade_history()
    assert history[0]["fee_amount"] == 0
