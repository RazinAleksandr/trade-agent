"""Polymarket fee calculation for realistic paper trading.

Fee formula (per Polymarket docs):
    fee = shares * price * fee_rate * (price * (1 - price)) ^ exponent

Fee parameters are category-specific. API lookup is preferred when
token_id is available; static category table is the fallback.
"""

import requests

from lib.logging_setup import get_logger

log = get_logger("fees")

# Category-specific fee parameters (March 2026 docs)
FEE_PARAMS = {
    "crypto":      {"fee_rate": 0.072, "exponent": 1},    # peak 1.80%
    "sports":      {"fee_rate": 0.03,  "exponent": 1},    # peak 0.75%
    "finance":     {"fee_rate": 0.04,  "exponent": 1},    # peak 1.00%
    "politics":    {"fee_rate": 0.04,  "exponent": 1},    # peak 1.00%
    "economics":   {"fee_rate": 0.03,  "exponent": 0.5},  # peak 1.50%
    "weather":     {"fee_rate": 0.025, "exponent": 0.5},  # peak 1.25%
    "culture":     {"fee_rate": 0.05,  "exponent": 1},    # peak 1.25%
    "tech":        {"fee_rate": 0.04,  "exponent": 1},    # peak 1.00%
    "mentions":    {"fee_rate": 0.25,  "exponent": 2},    # peak 1.56%
    "other":       {"fee_rate": 0.2,   "exponent": 2},    # peak 1.25%
    "geopolitics": {"fee_rate": 0,     "exponent": 0},    # no fee
}
DEFAULT_CATEGORY = "other"


def _get_fee_params(category: str) -> dict:
    """Get fee parameters for a category, defaulting to 'other' with warning."""
    cat = category.lower().strip() if category else ""
    if cat in FEE_PARAMS:
        return FEE_PARAMS[cat]
    log.warning(f"Unknown category '{category}', defaulting to '{DEFAULT_CATEGORY}'")
    return FEE_PARAMS[DEFAULT_CATEGORY]


def calculate_fee(shares: float, price: float, category: str) -> float:
    """Total fee in USDC for a trade. Rounded to 4 decimals per Polymarket rules.

    Args:
        shares: Number of shares traded.
        price: Share price (probability 0-1).
        category: Market category for fee parameter lookup.

    Returns:
        Fee in USDC, rounded to 4 decimal places. Returns 0 if below 0.0001.
    """
    params = _get_fee_params(category)
    fee_rate = params["fee_rate"]
    exponent = params["exponent"]

    if fee_rate == 0:
        return 0.0

    prob_factor = price * (1 - price)
    fee = shares * price * fee_rate * (prob_factor ** exponent)
    fee = round(fee, 4)

    # Minimum nonzero fee is 0.0001 USDC
    if fee < 0.0001:
        return 0.0

    return fee


def calculate_fee_per_share(price: float, category: str) -> float:
    """Per-share USDC-equivalent fee for effective price adjustment.

    This is the fee for 1 share, used to adjust fill prices.

    Args:
        price: Share price (probability 0-1).
        category: Market category for fee parameter lookup.

    Returns:
        Fee per share in USDC, rounded to 4 decimal places.
    """
    return calculate_fee(1.0, price, category)


def estimate_round_trip_fee_rate(price: float, category: str) -> float:
    """Combined entry+exit fee as fraction of notional (for edge adjustment).

    Estimates the round-trip fee cost assuming exit at the same price.
    Returns a fraction (e.g. 0.036 for 3.6% round-trip cost).

    Args:
        price: Share price (probability 0-1).
        category: Market category for fee parameter lookup.

    Returns:
        Round-trip fee as fraction of notional value.
    """
    if price <= 0 or price >= 1:
        return 0.0

    fee_per_share = calculate_fee_per_share(price, category)
    # Round trip = entry fee + exit fee (both at same price as estimate)
    round_trip_fee = 2 * fee_per_share
    # Express as fraction of share price (notional per share)
    return round(round_trip_fee / price, 6) if price > 0 else 0.0


def get_fee_rate_from_api(token_id: str, host: str) -> float | None:
    """Query CLOB API for market-specific fee rate.

    Uses the /fee-rate endpoint which returns base_fee in basis points.

    Args:
        token_id: CLOB token ID for the market outcome.
        host: CLOB API host URL.

    Returns:
        Fee rate as decimal (e.g. 0.018 for 180 bps) or None on failure.
    """
    try:
        url = f"{host}/fee-rate?token_id={token_id}"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        # API returns basis points (e.g. 180 for 1.80%)
        bps = float(data.get("base_fee", 0))
        if bps > 0:
            return bps / 10000  # Convert bps to decimal
        return None
    except Exception as e:
        log.warning(f"Fee rate API lookup failed for token {token_id}: {e}")
        return None
