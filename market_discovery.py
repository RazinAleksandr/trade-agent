import json
import requests
from dataclasses import dataclass
from typing import Optional
import config
from logger_setup import get_logger

log = get_logger("market_discovery")


@dataclass
class Market:
    id: str
    condition_id: str
    question: str
    description: str
    yes_token_id: str
    no_token_id: str
    yes_price: float
    no_price: float
    volume_24h: float
    liquidity: float
    end_date: str
    category: str
    active: bool
    closed: bool


def fetch_active_markets(
    limit: int = config.MAX_MARKETS_PER_CYCLE,
    min_volume: float = config.MIN_VOLUME_24H,
    min_liquidity: float = config.MIN_LIQUIDITY,
) -> list[Market]:
    """Fetch active, tradable markets from Gamma API with filters."""
    try:
        resp = requests.get(
            f"{config.GAMMA_API_URL}/markets",
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


def fetch_market_by_id(market_id: str) -> Optional[Market]:
    """Fetch a single market by its condition ID or slug."""
    try:
        resp = requests.get(
            f"{config.GAMMA_API_URL}/markets/{market_id}",
            timeout=30,
        )
        resp.raise_for_status()
        return _parse_market(resp.json())
    except Exception as e:
        log.error(f"Failed to fetch market {market_id}: {e}")
        return None


def fetch_events(limit: int = 10) -> list[dict]:
    """Fetch active events (groups of related markets)."""
    try:
        resp = requests.get(
            f"{config.GAMMA_API_URL}/events",
            params={
                "active": "true",
                "closed": "false",
                "order": "volume24hr",
                "ascending": "false",
                "limit": limit,
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        log.error(f"Failed to fetch events: {e}")
        return []


def _parse_market(m: dict) -> Optional[Market]:
    """Parse raw API response into Market dataclass."""
    tokens = m.get("clobTokenIds") or m.get("clob_token_ids")
    if not tokens or not isinstance(tokens, (list, str)):
        return None

    # Handle stringified JSON from Gamma API
    if isinstance(tokens, str):
        tokens = json.loads(tokens)

    if len(tokens) < 2:
        return None

    # Parse prices (also stringified JSON)
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
        volume_24h=float(m.get("volume24hr") or m.get("volume_num_24hr") or 0),
        liquidity=float(m.get("liquidityNum") or m.get("liquidity_num") or 0),
        end_date=m.get("endDate") or m.get("end_date_iso") or "",
        category=m.get("groupItemTitle") or m.get("category") or "",
        active=m.get("active", True),
        closed=m.get("closed", False),
    )


def _passes_filters(market: Market, min_volume: float, min_liquidity: float) -> bool:
    """Check if market passes our trading filters."""
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
