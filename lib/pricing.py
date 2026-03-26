"""CLOB API pricing for orderbook best bid/ask retrieval.

Uses py-clob-client's get_price() method which returns book-side prices.
CRITICAL: get_price() uses book-side semantics -- see get_fill_price() docs.

Does NOT use get_order_book() due to stale data issues (Pitfall 3 / GitHub #180).
"""

from py_clob_client.client import ClobClient

from lib.logging_setup import get_logger

log = get_logger("pricing")


def get_fill_price(token_id: str, trade_side: str, host: str) -> float:
    """Get realistic fill price from CLOB API for paper trade simulation.

    CRITICAL (Pitfall 1): get_price() uses book-side semantics:
    - get_price(token_id, 'BUY')  = best bid (highest buy order on book)
    - get_price(token_id, 'SELL') = best ask (lowest sell order on book)

    For taker fills (paper trades), we need the OPPOSITE side:
    - Paper BUY fills at best ask  -> call get_price(token_id, 'SELL')
    - Paper SELL fills at best bid -> call get_price(token_id, 'BUY')

    Args:
        token_id: CLOB token ID for the outcome.
        trade_side: "BUY" or "SELL" (taker perspective).
        host: CLOB API host URL (e.g. https://clob.polymarket.com).

    Returns:
        Fill price as float.

    Raises:
        ValueError: If price <= 0 (no liquidity) or invalid side.
    """
    if trade_side not in ("BUY", "SELL"):
        raise ValueError(f"Invalid trade side: {trade_side}. Must be 'BUY' or 'SELL'.")

    reader = ClobClient(host)

    if trade_side == "BUY":
        # Buyer fills at best ask (lowest sell order on book)
        result = reader.get_price(token_id, "SELL")
    else:
        # Seller fills at best bid (highest buy order on book)
        result = reader.get_price(token_id, "BUY")

    price = float(result.get("price", 0))
    if price <= 0:
        raise ValueError(f"No liquidity for {trade_side} on token {token_id}")
    return price


def get_best_bid(token_id: str, host: str) -> float:
    """Get the best bid price (highest buy order) from CLOB API.

    Args:
        token_id: CLOB token ID for the outcome.
        host: CLOB API host URL.

    Returns:
        Best bid price as float.

    Raises:
        ValueError: If price <= 0 (no bids on book).
    """
    reader = ClobClient(host)
    result = reader.get_price(token_id, "BUY")
    price = float(result.get("price", 0))
    if price <= 0:
        raise ValueError(f"No bid liquidity for token {token_id}")
    return price


def get_best_ask(token_id: str, host: str) -> float:
    """Get the best ask price (lowest sell order) from CLOB API.

    Args:
        token_id: CLOB token ID for the outcome.
        host: CLOB API host URL.

    Returns:
        Best ask price as float.

    Raises:
        ValueError: If price <= 0 (no asks on book).
    """
    reader = ClobClient(host)
    result = reader.get_price(token_id, "SELL")
    price = float(result.get("price", 0))
    if price <= 0:
        raise ValueError(f"No ask liquidity for token {token_id}")
    return price
