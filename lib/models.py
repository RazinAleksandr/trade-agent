from dataclasses import dataclass, asdict


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
    best_bid: float
    best_ask: float
    volume_24h: float
    liquidity: float
    end_date: str
    category: str
    active: bool
    closed: bool
    neg_risk: bool
    order_min_size: float
    tick_size: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TradeSignal:
    market_id: str
    question: str
    side: str  # "YES" or "NO"
    token_id: str
    price: float  # limit price
    size: float  # number of shares
    cost_usdc: float
    edge: float
    kelly_raw: float
    kelly_adjusted: float
    confidence: float
    reasoning: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class OrderResult:
    order_id: str
    success: bool
    message: str
    is_paper: bool

    def to_dict(self) -> dict:
        return asdict(self)
