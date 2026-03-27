"""Trade execution for paper and live modes.

Paper trades use realistic CLOB API pricing (best ask for buys).
Live trades create signed GTC limit orders via py-clob-client.
Both modes record trades to SQLite and update positions.
"""

import uuid

from py_clob_client.client import ClobClient
from py_clob_client.clob_types import OrderArgs, OrderType
from py_clob_client.exceptions import PolyApiException
from py_clob_client.order_builder.constants import BUY, SELL

from lib.models import OrderResult
from lib.db import DataStore
from lib.fees import calculate_fee, calculate_fee_per_share, get_fee_rate_from_api
from lib.pricing import get_fill_price
from lib.logging_setup import get_logger

log = get_logger("trading")


def validate_order(price: float, size: float,
                   order_min_size: float = 5.0) -> tuple[bool, str]:
    """Validate order parameters before execution.

    Checks price range (0, 1) and minimum notional (price * size >= order_min_size).
    Size is rounded to 2 decimal places before validation (SAFE-05).

    Args:
        price: Order price (must be between 0 and 1 exclusive).
        size: Number of shares (rounded to 2 decimals).
        order_min_size: Minimum order notional in USDC (default 5.0).

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    if price <= 0 or price >= 1:
        return (False, "Price must be between 0 and 1")

    size = round(size, 2)
    notional = price * size
    if notional < order_min_size:
        return (False,
                f"Order notional {notional:.2f} below minimum {order_min_size} USDC")

    return (True, "")


def execute_paper_trade(
    market_id: str,
    question: str,
    side: str,
    token_id: str,
    size: float,
    host: str,
    store: DataStore,
    condition_id: str = "",
    estimated_prob: float = 0,
    edge: float = 0,
    reasoning: str = "",
    neg_risk: bool = False,
    order_min_size: float = 5.0,
    category: str = "other",
) -> OrderResult:
    """Execute a paper trade with realistic CLOB API pricing and fee modeling.

    Paper buys fill at best ask from CLOB API (D-09). If CLOB API is
    unreachable, the trade fails with ValueError (D-10: no fake fills).
    Fees are modeled via effective price adjustment: position cost basis
    reflects fill_price + fee_per_share for accurate P&L tracking.

    Args:
        market_id: Polymarket market ID.
        question: Market question text (for record-keeping).
        side: "YES" or "NO" -- which outcome to buy.
        token_id: CLOB token ID for the outcome.
        size: Number of shares to buy.
        host: CLOB API host URL.
        store: DataStore instance for persistence.
        condition_id: Market condition ID (optional).
        estimated_prob: Estimated probability (for record-keeping).
        edge: Calculated edge (for record-keeping).
        reasoning: Trade reasoning (for record-keeping).
        neg_risk: Whether market uses neg-risk exchange.
        order_min_size: Minimum order notional in USDC.
        category: Market category for fee calculation (default: "other").

    Returns:
        OrderResult with paper trade details.

    Raises:
        ValueError: If CLOB API is unreachable or has no liquidity (D-10).
    """
    # We always BUY the token we believe in (YES or NO)
    # get_fill_price handles the inversion: BUY trade -> queries SELL book -> best ask
    fill_price = get_fill_price(token_id, "BUY", host)

    # Round size to 2 decimal places (SAFE-05)
    size = round(size, 2)

    # Validate order
    valid, msg = validate_order(fill_price, size, order_min_size)
    if not valid:
        return OrderResult(order_id="", success=False, message=msg, is_paper=True)

    # Calculate fee: API-first lookup, fall back to category table
    api_rate = get_fee_rate_from_api(token_id, host)
    if api_rate is not None:
        fee_per_share = round(api_rate * fill_price, 4)
        fee_amount = round(api_rate * fill_price * size, 4)
    else:
        fee_per_share = calculate_fee_per_share(fill_price, category)
        fee_amount = calculate_fee(size, fill_price, category)

    # Fee-adjusted effective price: costlier entry
    effective_price = fill_price + fee_per_share

    # Generate paper order ID
    order_id = f"paper-{uuid.uuid4().hex[:12]}"

    # Record trade with actual fill price; fee tracked separately
    store.record_trade(
        market_id=market_id,
        question=question,
        side=side,
        price=fill_price,
        size=size,
        token_id=token_id,
        condition_id=condition_id,
        order_id=order_id,
        is_paper=True,
        estimated_prob=estimated_prob,
        edge=edge,
        reasoning=reasoning,
        neg_risk=neg_risk,
        fill_price=fill_price,
        fee_amount=fee_amount,
    )

    # Position uses fee-adjusted effective price for accurate P&L
    store.upsert_position(
        market_id=market_id,
        question=question,
        side=side,
        price=effective_price,
        size=size,
        token_id=token_id,
    )

    log.info(
        f"[PAPER] {side} {size:.2f} shares @ ${fill_price:.3f} "
        f"(eff ${effective_price:.4f}, fee ${fee_amount:.4f}) "
        f"on '{question[:50]}'"
    )

    return OrderResult(
        order_id=order_id,
        success=True,
        message="Paper trade executed",
        is_paper=True,
    )


def execute_live_trade(
    market_id: str,
    question: str,
    side: str,
    token_id: str,
    price: float,
    size: float,
    host: str,
    private_key: str,
    chain_id: int,
    store: DataStore,
    condition_id: str = "",
    estimated_prob: float = 0,
    edge: float = 0,
    reasoning: str = "",
    neg_risk: bool = False,
    order_min_size: float = 5.0,
) -> OrderResult:
    """Execute a live trade via py-clob-client with signed GTC limit order.

    Creates an authenticated ClobClient, signs and posts a GTC limit order.
    Uses signature_type=0 for EOA wallets. Always uses BUY side (we buy
    the token -- YES or NO -- that we believe in).

    Args:
        market_id: Polymarket market ID.
        question: Market question text (for record-keeping).
        side: "YES" or "NO" -- which outcome to buy.
        token_id: CLOB token ID for the outcome.
        price: Limit price for the order.
        size: Number of shares to buy.
        host: CLOB API host URL.
        private_key: Ethereum private key for signing.
        chain_id: Chain ID (137 for Polygon).
        store: DataStore instance for persistence.
        condition_id: Market condition ID (optional).
        estimated_prob: Estimated probability (for record-keeping).
        edge: Calculated edge (for record-keeping).
        reasoning: Trade reasoning (for record-keeping).
        neg_risk: Whether market uses neg-risk exchange.
        order_min_size: Minimum order notional in USDC.

    Returns:
        OrderResult with live trade details.
    """
    # Round size to 2 decimal places (SAFE-05)
    size = round(size, 2)

    # Validate order
    valid, msg = validate_order(price, size, order_min_size)
    if not valid:
        return OrderResult(order_id="", success=False, message=msg, is_paper=False)

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            # Create authenticated ClobClient with signature_type=0 (EOA wallets)
            client = ClobClient(
                host,
                key=private_key,
                chain_id=chain_id,
                signature_type=0,
            )
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)

            # Create order -- always BUY the token we believe in
            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=BUY,
            )

            # Sign and post as GTC limit order
            signed = client.create_order(order_args)
            result = client.post_order(signed, OrderType.GTC)

            order_id = result.get("orderID", result.get("id", "unknown"))

            # Record trade
            store.record_trade(
                market_id=market_id,
                question=question,
                side=side,
                price=price,
                size=size,
                token_id=token_id,
                condition_id=condition_id,
                order_id=order_id,
                is_paper=False,
                estimated_prob=estimated_prob,
                edge=edge,
                reasoning=reasoning,
                neg_risk=neg_risk,
                fill_price=price,
            )

            # Update position
            store.upsert_position(
                market_id=market_id,
                question=question,
                side=side,
                price=price,
                size=size,
                token_id=token_id,
            )

            log.info(
                f"[LIVE] {side} {size:.2f} shares @ ${price:.3f} "
                f"on '{question[:50]}' -- order: {order_id}"
            )

            return OrderResult(
                order_id=order_id,
                success=True,
                message=str(result),
                is_paper=False,
            )

        except PolyApiException as e:
            if e.status_code == 401 and attempt < max_retries:
                log.warning(
                    f"CLOB API returned 401, re-deriving credentials "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                continue  # retry with fresh credentials
            log.error(f"Live trade failed: {e}")
            return OrderResult(
                order_id="",
                success=False,
                message=str(e),
                is_paper=False,
            )
        except Exception as e:
            log.error(f"Live trade failed: {e}")
            return OrderResult(
                order_id="",
                success=False,
                message=str(e),
                is_paper=False,
            )

    # Should not reach here, but safety return
    return OrderResult(
        order_id="", success=False,
        message="Max retries exceeded", is_paper=False,
    )


def execute_paper_sell(
    market_id: str,
    question: str,
    side: str,
    token_id: str,
    size: float,
    host: str,
    store: DataStore,
    reasoning: str = "",
    order_min_size: float = 5.0,
    category: str = "other",
) -> OrderResult:
    """Execute a paper sell with realistic CLOB API pricing and fee modeling.

    Sells fill at best bid from CLOB API. If CLOB API is unreachable,
    the trade fails with ValueError (no fake fills). Fees are collected
    in USDC on sells: effective_price = fill_price - fee_per_share.

    Args:
        market_id: Polymarket market ID.
        question: Market question text (for record-keeping).
        side: "YES" or "NO" -- which outcome to sell.
        token_id: CLOB token ID for the outcome.
        size: Number of shares to sell.
        host: CLOB API host URL.
        store: DataStore instance for persistence.
        reasoning: Sell reasoning (for record-keeping).
        order_min_size: Minimum order notional in USDC.
        category: Market category for fee calculation (default: "other").

    Returns:
        OrderResult with paper sell details.

    Raises:
        ValueError: If CLOB API is unreachable or has no liquidity.
    """
    # Seller fills at best bid (highest buy order on book)
    fill_price = get_fill_price(token_id, "SELL", host)

    size = round(size, 2)

    valid, msg = validate_order(fill_price, size, order_min_size)
    if not valid:
        return OrderResult(order_id="", success=False, message=msg, is_paper=True)

    # Calculate fee: API-first lookup, fall back to category table
    api_rate = get_fee_rate_from_api(token_id, host)
    if api_rate is not None:
        fee_per_share = round(api_rate * fill_price, 4)
        fee_amount = round(api_rate * fill_price * size, 4)
    else:
        fee_per_share = calculate_fee_per_share(fill_price, category)
        fee_amount = calculate_fee(size, fill_price, category)

    # Fee-adjusted effective price: lower proceeds on sell
    effective_price = fill_price - fee_per_share

    order_id = f"paper-sell-{uuid.uuid4().hex[:12]}"

    # Reduce/close position using fee-adjusted effective price
    realized_pnl = store.reduce_position(market_id, size, effective_price)

    # Record sell trade with actual fill price; fee tracked separately
    store.record_trade(
        market_id=market_id,
        question=question,
        side=side,
        price=fill_price,
        size=size,
        token_id=token_id,
        order_id=order_id,
        is_paper=True,
        reasoning=reasoning,
        fill_price=fill_price,
        action="SELL",
        fee_amount=fee_amount,
    )

    log.info(
        f"[PAPER SELL] {side} {size:.2f} shares @ ${fill_price:.3f} "
        f"(eff ${effective_price:.4f}, fee ${fee_amount:.4f}) "
        f"on '{question[:50]}' PnL=${realized_pnl:.2f}"
    )

    return OrderResult(
        order_id=order_id,
        success=True,
        message=f"Paper sell executed, realized PnL: ${realized_pnl:.2f}",
        is_paper=True,
    )


def execute_live_sell(
    market_id: str,
    question: str,
    side: str,
    token_id: str,
    price: float,
    size: float,
    host: str,
    private_key: str,
    chain_id: int,
    store: DataStore,
    reasoning: str = "",
    order_min_size: float = 5.0,
) -> OrderResult:
    """Execute a live sell via py-clob-client with signed GTC limit order.

    Args:
        market_id: Polymarket market ID.
        question: Market question text (for record-keeping).
        side: "YES" or "NO" -- which outcome to sell.
        token_id: CLOB token ID for the outcome.
        price: Limit price for the sell order.
        size: Number of shares to sell.
        host: CLOB API host URL.
        private_key: Ethereum private key for signing.
        chain_id: Chain ID (137 for Polygon).
        store: DataStore instance for persistence.
        reasoning: Sell reasoning (for record-keeping).
        order_min_size: Minimum order notional in USDC.

    Returns:
        OrderResult with live sell details.
    """
    size = round(size, 2)

    valid, msg = validate_order(price, size, order_min_size)
    if not valid:
        return OrderResult(order_id="", success=False, message=msg, is_paper=False)

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            client = ClobClient(
                host,
                key=private_key,
                chain_id=chain_id,
                signature_type=0,
            )
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)

            order_args = OrderArgs(
                token_id=token_id,
                price=price,
                size=size,
                side=SELL,
            )

            signed = client.create_order(order_args)
            result = client.post_order(signed, OrderType.GTC)

            order_id = result.get("orderID", result.get("id", "unknown"))

            # Reduce/close position and get realized PnL
            realized_pnl = store.reduce_position(market_id, size, price)

            # Record sell trade
            store.record_trade(
                market_id=market_id,
                question=question,
                side=side,
                price=price,
                size=size,
                token_id=token_id,
                order_id=order_id,
                is_paper=False,
                reasoning=reasoning,
                fill_price=price,
                action="SELL",
            )

            log.info(
                f"[LIVE SELL] {side} {size:.2f} shares @ ${price:.3f} "
                f"on '{question[:50]}' PnL=${realized_pnl:.2f} -- order: {order_id}"
            )

            return OrderResult(
                order_id=order_id,
                success=True,
                message=f"Live sell executed, realized PnL: ${realized_pnl:.2f}",
                is_paper=False,
            )

        except PolyApiException as e:
            if e.status_code == 401 and attempt < max_retries:
                log.warning(
                    f"CLOB API returned 401, re-deriving credentials "
                    f"(attempt {attempt + 1}/{max_retries})"
                )
                continue
            log.error(f"Live sell failed: {e}")
            return OrderResult(
                order_id="", success=False, message=str(e), is_paper=False,
            )
        except Exception as e:
            log.error(f"Live sell failed: {e}")
            return OrderResult(
                order_id="", success=False, message=str(e), is_paper=False,
            )

    return OrderResult(
        order_id="", success=False,
        message="Max retries exceeded", is_paper=False,
    )
