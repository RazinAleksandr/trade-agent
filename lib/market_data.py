"""Gamma API client for market discovery and retrieval.

Cherry-picked and adapted from v1 market_discovery.py with additions:
- neg_risk, best_bid, best_ask, order_min_size, tick_size fields
- Explicit parameter passing (no global config import)
- Returns lib.models.Market dataclass instances
"""

import json

import requests

from lib.logging_setup import get_logger
from lib.models import Market

log = get_logger("market_data")


def fetch_active_markets(
    gamma_api_url: str,
    min_volume: float = 1000.0,
    min_liquidity: float = 500.0,
    limit: int = 10,
) -> list[Market]:
    """Fetch active, tradable markets from Gamma API with filters.

    Args:
        gamma_api_url: Base URL for Gamma API (e.g. https://gamma-api.polymarket.com).
        min_volume: Minimum 24h volume in USDC.
        min_liquidity: Minimum liquidity in USDC.
        limit: Maximum number of markets to return.

    Returns:
        List of Market objects passing all filters, sorted by volume descending.
        Returns empty list on any API error (safe default).
    """
    try:
        resp = requests.get(
            f"{gamma_api_url}/markets",
            params={
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": 50,  # fetch more, filter locally
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw_markets = resp.json()
    except Exception as e:
        log.error(f"Failed to fetch markets: {e}")
        return []

    markets = []
    for m in raw_markets:
        try:
            market = _parse_market(m)
            if market and _passes_filters(market, min_volume, min_liquidity):
                markets.append(market)
        except Exception as e:
            log.warning(f"Failed to parse market {m.get('question', '?')}: {e}")
            continue

    markets = markets[:limit]
    log.info(f"Discovered {len(markets)} tradable markets")
    return markets


def fetch_market_by_id(gamma_api_url: str, market_id: str) -> Market | None:
    """Fetch a single market by its condition ID or slug.

    Args:
        gamma_api_url: Base URL for Gamma API.
        market_id: Market condition ID or slug.

    Returns:
        Market object or None on error.
    """
    try:
        resp = requests.get(
            f"{gamma_api_url}/markets/{market_id}",
            timeout=30,
        )
        resp.raise_for_status()
        return _parse_market(resp.json())
    except Exception as e:
        log.error(f"Failed to fetch market {market_id}: {e}")
        return None


def _parse_market(m: dict) -> Market | None:
    """Parse raw Gamma API response into a Market dataclass.

    CRITICAL: clobTokenIds and outcomePrices are stringified JSON fields --
    they arrive as strings containing JSON arrays, not native lists.
    Must use json.loads() to parse them (Pitfall 2).

    Handles both camelCase (API default) and snake_case field names.
    """
    # Parse token IDs -- handle both camelCase and snake_case
    tokens = m.get("clobTokenIds") or m.get("clob_token_ids")
    if not tokens or not isinstance(tokens, (list, str)):
        return None

    # Handle stringified JSON from Gamma API
    if isinstance(tokens, str):
        tokens = json.loads(tokens)

    if len(tokens) < 2:
        return None

    # Parse outcome prices (also stringified JSON)
    outcome_prices = m.get("outcomePrices") or m.get("outcome_prices") or "[]"
    if isinstance(outcome_prices, str):
        outcome_prices = json.loads(outcome_prices)

    yes_price = float(outcome_prices[0]) if len(outcome_prices) > 0 and outcome_prices[0] else 0.5
    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 and outcome_prices[1] else 0.5

    return Market(
        id=str(m.get("id", "")),
        condition_id=m.get("conditionId") or m.get("condition_id") or "",
        question=m.get("question", ""),
        description=m.get("description", ""),
        yes_token_id=tokens[0],
        no_token_id=tokens[1],
        yes_price=yes_price,
        no_price=no_price,
        best_bid=float(m.get("bestBid") or 0),
        best_ask=float(m.get("bestAsk") or 0),
        volume_24h=float(m.get("volume24hr") or m.get("volume_num_24hr") or 0),
        liquidity=float(m.get("liquidityNum") or m.get("liquidity_num") or 0),
        end_date=m.get("endDate") or m.get("end_date_iso") or "",
        category=m.get("groupItemTitle") or m.get("category") or "",
        active=m.get("active", True),
        closed=m.get("closed", False),
        neg_risk=m.get("negRisk", False),
        order_min_size=float(m.get("orderMinSize") or 5),
        tick_size=float(m.get("orderPriceMinTickSize") or 0.01),
    )


def _passes_filters(market: Market, min_volume: float, min_liquidity: float) -> bool:
    """Check if market passes trading filters.

    Rejects:
    - Closed or inactive markets
    - Markets with volume below min_volume
    - Markets with liquidity below min_liquidity
    - Markets with extreme prices (< 0.05 or > 0.95) -- no edge opportunity
    - Markets with missing token IDs
    """
    if market.closed or not market.active:
        return False
    if market.volume_24h < min_volume:
        return False
    if market.liquidity < min_liquidity:
        return False
    # Skip markets with prices too close to 0 or 1 (no edge opportunity)
    if market.yes_price < 0.05 or market.yes_price > 0.95:
        return False
    # Must have valid token IDs
    if not market.yes_token_id or not market.no_token_id:
        return False
    return True
