import math
from dataclasses import dataclass
from market_analyzer import MarketAnalysis
from data_store import DataStore
import config
from logger_setup import get_logger, log_decision

log = get_logger("strategy")


@dataclass
class TradeSignal:
    market_id: str
    question: str
    side: str          # "YES" or "NO"
    token_id: str
    price: float       # limit price
    size: float        # number of shares
    cost_usdc: float
    edge: float
    kelly_raw: float
    kelly_adjusted: float
    confidence: float
    reasoning: str


def kelly_criterion(prob: float, odds_price: float, fraction: float = config.KELLY_FRACTION) -> float:
    """
    Fractional Kelly criterion for binary outcome.
    prob: estimated true probability of winning
    odds_price: price we pay per share (payout is 1.0 on win)
    fraction: Kelly fraction (0.25 = quarter Kelly for safety)

    Returns fraction of bankroll to bet.
    """
    if odds_price <= 0 or odds_price >= 1:
        return 0

    # Net odds: if we pay p, we win (1-p) on success
    b = (1 - odds_price) / odds_price  # net odds
    q = 1 - prob  # probability of losing

    kelly = (b * prob - q) / b
    kelly = max(0, kelly)  # no negative bets

    return kelly * fraction


def generate_signals(
    analyses: list[MarketAnalysis],
    store: DataStore,
    bankroll: float = config.MAX_TOTAL_EXPOSURE_USDC,
) -> list[TradeSignal]:
    """Generate trade signals from market analyses."""
    signals = []
    current_exposure = store.get_total_exposure()
    remaining_capital = bankroll - current_exposure

    if remaining_capital <= 0:
        log.info("Max exposure reached, no new trades")
        return []

    open_positions = {p["market_id"] for p in store.get_open_positions()}

    for analysis in analyses:
        # Skip markets we already have positions in
        if analysis.market_id in open_positions:
            continue

        # Determine direction and parameters
        signal = _evaluate_signal(analysis, remaining_capital)
        if signal:
            signals.append(signal)
            remaining_capital -= signal.cost_usdc

            log_decision(log, "trade_signal", {
                "market_id": signal.market_id,
                "question": signal.question[:80],
                "side": signal.side,
                "price": signal.price,
                "size": signal.size,
                "cost": signal.cost_usdc,
                "edge": signal.edge,
                "kelly": signal.kelly_adjusted,
            })

        if remaining_capital <= 0:
            break

    log.info(f"Generated {len(signals)} trade signals from {len(analyses)} analyses")
    return signals


def _evaluate_signal(
    analysis: MarketAnalysis,
    available_capital: float,
) -> TradeSignal | None:
    """Evaluate a single analysis and return a trade signal if edge is sufficient."""
    abs_edge = abs(analysis.edge)

    # Must exceed minimum edge threshold
    if abs_edge < config.MIN_EDGE_THRESHOLD:
        return None

    # Confidence-adjusted edge
    effective_edge = abs_edge * analysis.confidence
    if effective_edge < config.MIN_EDGE_THRESHOLD * 0.5:
        return None

    # Determine direction
    if analysis.edge > 0:
        # We think YES is underpriced → buy YES
        side = "YES"
        price = analysis.market_price  # buy at current price
        prob = analysis.estimated_prob
    else:
        # We think YES is overpriced → buy NO
        side = "NO"
        price = 1.0 - analysis.market_price  # NO price
        prob = 1.0 - analysis.estimated_prob

    # Kelly sizing
    kelly_raw = kelly_criterion(prob, price, fraction=1.0)
    kelly_adjusted = kelly_criterion(prob, price, fraction=config.KELLY_FRACTION)

    if kelly_adjusted <= 0:
        return None

    # Position size in USDC
    position_size = min(
        kelly_adjusted * available_capital,
        config.MAX_POSITION_SIZE_USDC,
        available_capital,
    )

    if position_size < 1.0:  # minimum $1 trade
        return None

    # Number of shares = position_size / price
    num_shares = position_size / price

    return TradeSignal(
        market_id=analysis.market_id,
        question=analysis.question,
        side=side,
        token_id="",  # filled by trader from market data
        price=round(price, 2),
        size=round(num_shares, 2),
        cost_usdc=round(position_size, 2),
        edge=round(analysis.edge, 4),
        kelly_raw=round(kelly_raw, 4),
        kelly_adjusted=round(kelly_adjusted, 4),
        confidence=analysis.confidence,
        reasoning=analysis.reasoning,
    )
