"""Kelly criterion, edge calculation, and position sizing.

Pure-math strategy functions with no API dependencies.
Cherry-picked from v1 strategy.py with improved interface.
"""


def kelly_criterion(prob: float, odds_price: float, fraction: float = 0.25) -> float:
    """Fractional Kelly criterion for binary outcome.

    Args:
        prob: Estimated true probability of winning (0.0-1.0).
        odds_price: Price per share -- payout is 1.0 on win (0.0-1.0).
        fraction: Kelly fraction for conservative sizing (0.25 = quarter Kelly).

    Returns:
        Fraction of bankroll to bet (0.0 if no edge or invalid price).
    """
    if odds_price <= 0 or odds_price >= 1:
        return 0.0

    # Net odds: if we pay p, we win (1-p) on success
    b = (1 - odds_price) / odds_price
    q = 1 - prob

    kelly = (b * prob - q) / b
    kelly = max(0.0, kelly)  # no negative bets

    return kelly * fraction


def calculate_edge(estimated_prob: float, market_price: float,
                   fee_adjustment: float = 0.0) -> float:
    """Calculate edge as estimated probability minus market price minus fees.

    Positive edge = underpriced (buy opportunity).
    Negative edge = overpriced.

    Args:
        estimated_prob: Estimated true probability (0.0-1.0).
        market_price: Current market price (0.0-1.0).
        fee_adjustment: Round-trip fee cost to subtract from edge (default 0.0).

    Returns:
        Edge value rounded to 6 decimal places.
    """
    return round(estimated_prob - market_price - fee_adjustment, 6)


def calculate_position_size(
    prob: float,
    price: float,
    bankroll: float,
    kelly_fraction: float = 0.25,
    max_position_usdc: float = 50.0,
    order_min_size: float = 5.0,
) -> dict:
    """Calculate position size using Kelly criterion with caps and minimums.

    Args:
        prob: Estimated true probability of winning (0.0-1.0).
        price: Price per share (0.0-1.0).
        bankroll: Available bankroll in USDC.
        kelly_fraction: Kelly fraction for conservative sizing (default 0.25).
        max_position_usdc: Maximum position size in USDC.
        order_min_size: Minimum order size in USDC (SAFE-05: 5 USDC).

    Returns:
        Dict with keys: size_usdc, num_shares, kelly_raw, kelly_adjusted.
    """
    kelly_raw = kelly_criterion(prob, price, fraction=1.0)
    kelly_adjusted = kelly_criterion(prob, price, fraction=kelly_fraction)

    if kelly_adjusted <= 0:
        return {
            "size_usdc": 0.0,
            "num_shares": 0.0,
            "kelly_raw": round(kelly_raw, 6),
            "kelly_adjusted": 0.0,
        }

    position_usdc = min(kelly_adjusted * bankroll, max_position_usdc, bankroll)

    # SAFE-05: below minimum order size
    if position_usdc < order_min_size:
        return {
            "size_usdc": 0.0,
            "num_shares": 0.0,
            "kelly_raw": round(kelly_raw, 6),
            "kelly_adjusted": round(kelly_adjusted, 6),
        }

    # 2 decimal places per SAFE-05
    num_shares = round(position_usdc / price, 2)

    return {
        "size_usdc": round(position_usdc, 2),
        "num_shares": num_shares,
        "kelly_raw": round(kelly_raw, 6),
        "kelly_adjusted": round(kelly_adjusted, 6),
    }
