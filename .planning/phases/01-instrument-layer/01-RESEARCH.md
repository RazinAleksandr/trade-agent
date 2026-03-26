# Phase 1: Instrument Layer - Research

**Researched:** 2026-03-26
**Domain:** Python CLI tools for Polymarket trading (market data, order execution, portfolio tracking)
**Confidence:** HIGH

## Summary

Phase 1 builds a set of stateless Python CLI tools under `tools/` with shared logic in `lib/`. The existing v1 codebase has proven, working implementations of every core function needed (market discovery, trading, portfolio tracking, Kelly criterion, SQLite persistence, dual logging). The primary work is restructuring into the new `tools/` + `lib/` architecture, hardening the CLI interface (argparse, JSON output, error codes), and fixing paper trade pricing to use real orderbook data (best ask for buys, best bid for sells) instead of mid-price.

The py-clob-client library (v0.34.6, already installed) provides all needed CLOB API methods. A critical finding: `get_price(token_id, 'BUY')` returns the **best bid** (book-side semantics), not the best ask. Paper trade fills must use the **opposite** side: `get_price(token_id, 'SELL')` for buy fills and `get_price(token_id, 'BUY')` for sell fills. The Gamma API also provides `bestBid` and `bestAsk` fields directly on market objects, but CLOB API is the authoritative source per D-09. The `orderMinSize` (5 USDC) and `orderPriceMinTickSize` fields from Gamma API align with SAFE-05 requirements.

**Primary recommendation:** Cherry-pick v1 logic into `lib/` modules, build thin CLI wrappers in `tools/`, and test against live APIs. The architecture is straightforward -- the main risk is the counter-intuitive `get_price` side semantics and ensuring proper neg-risk market detection.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Tools use `argparse` for argument parsing. Auto-generated `--help`. Agent passes flags like `--min-volume 1000 --format json`.
- **D-02:** All tools output JSON to stdout. Human-readable mode via `--pretty` flag. No table format -- JSON only.
- **D-03:** Errors reported as JSON to stderr (`{"error": "message", "code": "INVALID_ARG"}`) with non-zero exit codes. Different exit codes for different error types.
- **D-04:** Each tool is a single-purpose script -- one script per action (e.g., `discover_markets.py`, `get_prices.py`, `execute_trade.py`, `get_portfolio.py`). No subcommands.
- **D-05:** Shared code lives in `lib/` package (config, db, models, logging). `tools/` has CLI entry points that import from `lib/`. Clean separation of CLI from reusable logic.
- **D-06:** Old v1 root `.py` files (main.py, market_discovery.py, trader.py, etc.) are deleted after cherry-picking useful logic into `tools/` + `lib/`. No legacy files left in root.
- **D-07:** Config continues to load from `.env` via `python-dotenv`. Each tool imports from `lib/config.py`. Same proven pattern as v1.
- **D-08:** Tools accept CLI flag overrides for config values (e.g., `--min-volume 5000` overrides `MIN_VOLUME_24H` from `.env`). Env vars are defaults, flags override.
- **D-09:** Paper buys fill at best ask, sells at best bid from CLOB API orderbook snapshot. Live orderbook data required even in paper mode (satisfies SAFE-02).
- **D-10:** If CLOB API is unreachable during paper trading, the trade fails with a clear error. No fake fills. Agent retries next cycle. Data integrity preserved.
- **D-11:** Paper mode requires network access to CLOB API read endpoints (orderbook, prices) but no private key or wallet. Only live trading needs wallet credentials.

### Claude's Discretion
- Exact argparse flag naming conventions per tool
- Internal JSON schema structure for each tool's output
- SQLite schema evolution from v1 (adapt tables or fresh schema)
- Logging format and verbosity levels
- Kelly criterion implementation details (same math, new interface)
- SIGINT/SIGTERM handler implementation approach
- Neg-risk market detection logic

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INST-01 | Python CLI tool fetches active markets from Gamma API filtered by volume, liquidity, and price range | Gamma API `/markets` endpoint verified live. v1 `market_discovery.py` has working `fetch_active_markets()` with filters. Gamma API returns `bestBid`/`bestAsk`, `negRisk`, `orderMinSize`, `orderPriceMinTickSize` fields. |
| INST-02 | Python CLI tool retrieves current orderbook prices for a given market from CLOB API | `get_price(token_id, side)` verified live. `get_order_book(token_id)` returns `OrderBookSummary` with bids/asks. Note: `get_price('BUY')` = best bid, `get_price('SELL')` = best ask (book-side semantics). |
| INST-03 | Python CLI tool calculates edge (estimated probability - market price) | v1 `strategy.py` has working edge calculation. Pure math, no API dependency. Edge = estimated_prob - market_price. |
| INST-04 | Python CLI tool computes Kelly criterion position size | v1 `strategy.py` has verified `kelly_criterion()` function. Tested in `test_paper_trading.py`. Pure math. |
| INST-05 | Python CLI tool executes paper trades with configurable spread | v1 `trader.py` has `_paper_trade()`. Needs upgrade: must use CLOB API best ask/bid pricing (D-09) instead of signal price. |
| INST-06 | Python CLI tool executes live trades via py-clob-client | v1 `trader.py` has `_live_trade()` with GTC limit orders. py-clob-client handles neg-risk automatically via `get_neg_risk(token_id)`. |
| INST-07 | Python CLI tool tracks open positions with unrealized/realized P&L | v1 `portfolio.py` has `PortfolioManager` with P&L calculation. v1 `data_store.py` has position CRUD. |
| INST-08 | Python CLI tool detects resolved markets and finalizes P&L | v1 `portfolio.py` has `check_for_resolved_markets()`. Checks `market.closed` flag from Gamma API. |
| INST-09 | Python CLI tool handles negative-risk markets (separate exchange contract) | Gamma API has `negRisk` boolean on markets. py-clob-client's `get_neg_risk(token_id)` and `create_order()` handle routing automatically. Neg-risk exchange: `0xC5d563A36AE78145C45a50134d48A1215220f80a`. |
| INST-10 | SQLite persistence stores trades, positions, decisions, market snapshots, strategy metrics | v1 `data_store.py` has full 5-table schema, verified with tests. Can reuse or adapt. |
| INST-11 | All parameters configurable via .env file | v1 `config.py` loads 18 parameters from `.env`. D-08 adds CLI flag overrides on top. |
| INST-12 | Graceful shutdown on SIGINT/SIGTERM | v1 `main.py` has `signal_handler()` pattern. For CLI tools: register handler, set flag, complete current op, exit cleanly. |
| INST-13 | Dual logging -- human-readable console + structured JSON file | v1 `logger_setup.py` has `get_logger()` with console + JSON file handlers. Directly reusable. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| py-clob-client | 0.34.6 (installed) | Polymarket CLOB API client | Official Polymarket SDK. Handles order signing, orderbook, pricing, neg-risk routing. |
| requests | 2.32.5 (installed) | Gamma API HTTP client | Standard Python HTTP library. Already used in v1 for market discovery. |
| python-dotenv | 1.2.2 (installed) | .env file loading | Already used in v1. D-07 requires continuing this pattern. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| eth-account | 0.13.7 (installed) | Wallet management | Only for live trading mode (INST-06). Not needed for paper mode. |
| web3 | 7.14.1 (installed) | Polygon on-chain operations | Only for `setup_wallet.py` token allowances. Not used in tools directly. |
| pytest | 9.0.2 (installed) | Test framework | For all test files. Already available. |

### Not Needed for Phase 1
| Library | Reason |
|---------|--------|
| openai | Market analysis is Phase 2 (agent layer). INST-03 edge calculation takes estimated_prob as input. |
| anthropic | Agent layer only (Phase 2). |

**Installation:** All packages already installed in `.venv/`. No new packages needed.

## Architecture Patterns

### Recommended Project Structure
```
tools/                       # CLI entry points (one file per tool)
    discover_markets.py      # INST-01: Market discovery
    get_prices.py            # INST-02: Orderbook prices
    calculate_edge.py        # INST-03: Edge calculation
    calculate_kelly.py       # INST-04: Kelly criterion sizing
    execute_trade.py         # INST-05/06: Paper and live trade execution
    get_portfolio.py         # INST-07: Portfolio with P&L
    check_resolved.py        # INST-08: Resolved market detection
lib/                         # Shared logic (Python package with __init__.py)
    __init__.py
    config.py                # .env loading + CLI override support (from v1 config.py)
    db.py                    # SQLite DataStore class (from v1 data_store.py)
    models.py                # Dataclasses: Market, TradeSignal, OrderResult, etc.
    market_data.py           # Gamma API client functions (from v1 market_discovery.py)
    pricing.py               # CLOB API price fetching (best bid/ask, orderbook)
    trading.py               # Paper + live trade execution (from v1 trader.py)
    portfolio.py             # Position tracking, P&L, risk limits (from v1 portfolio.py)
    strategy.py              # Kelly criterion, edge calculation (from v1 strategy.py)
    logging.py               # Dual logger setup (from v1 logger_setup.py)
    signals.py               # SIGINT/SIGTERM handler (from v1 main.py pattern)
tests/
    test_paper_trading.py    # Existing smoke tests (keep, adapt to new structure)
    conftest.py              # Shared test fixtures
    test_config.py           # Config loading and CLI override tests
    test_market_data.py      # Gamma API integration tests
    test_pricing.py          # CLOB API pricing tests (best bid/ask)
    test_trading.py          # Paper trade pricing, live trade flow
    test_portfolio.py        # P&L calculation, resolved market detection
    test_kelly.py            # Kelly criterion and edge calculation
    test_cli.py              # CLI argument parsing, JSON output, error codes
```

### Pattern 1: CLI Tool Structure
**What:** Each tool is a standalone argparse script that imports from `lib/`, outputs JSON to stdout, errors to stderr.
**When to use:** Every tool in `tools/`.
**Example:**
```python
#!/usr/bin/env python3
"""Discover active markets from Polymarket."""
import argparse
import json
import sys
import signal

from lib.config import load_config
from lib.market_data import fetch_active_markets
from lib.logging import get_logger
from lib.signals import register_shutdown_handler

def main():
    parser = argparse.ArgumentParser(description="Discover active Polymarket markets")
    parser.add_argument("--min-volume", type=float, help="Min 24h volume (USDC)")
    parser.add_argument("--min-liquidity", type=float, help="Min liquidity (USDC)")
    parser.add_argument("--limit", type=int, help="Max markets to return")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON output")
    args = parser.parse_args()

    config = load_config(args)  # .env defaults, CLI overrides
    log = get_logger("discover_markets")
    register_shutdown_handler()

    try:
        markets = fetch_active_markets(
            min_volume=config.min_volume_24h,
            min_liquidity=config.min_liquidity,
            limit=config.max_markets_per_cycle,
        )
        output = [m.to_dict() for m in markets]
        indent = 2 if args.pretty else None
        json.dump(output, sys.stdout, indent=indent)
        sys.stdout.write("\n")
    except Exception as e:
        log.error(f"Discovery failed: {e}")
        json.dump({"error": str(e), "code": "DISCOVERY_FAILED"}, sys.stderr)
        sys.stderr.write("\n")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Pattern 2: Config with CLI Override
**What:** Config loads from .env first, then CLI flags override specific values.
**When to use:** Every tool (D-07, D-08).
**Example:**
```python
# lib/config.py
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()

@dataclass
class Config:
    paper_trading: bool = True
    min_volume_24h: float = 1000.0
    min_liquidity: float = 500.0
    max_markets_per_cycle: int = 10
    min_edge_threshold: float = 0.10
    kelly_fraction: float = 0.25
    max_position_size_usdc: float = 50.0
    max_total_exposure_usdc: float = 200.0
    db_path: str = "trading.db"
    log_level: str = "INFO"
    log_file: str = "trading.log"
    polymarket_host: str = "https://clob.polymarket.com"
    gamma_api_url: str = "https://gamma-api.polymarket.com"
    chain_id: int = 137
    private_key: str = ""

def load_config(args=None) -> Config:
    """Load config from .env, then override with CLI args if present."""
    config = Config(
        paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
        min_volume_24h=float(os.getenv("MIN_VOLUME_24H", "1000")),
        # ... etc for all params
    )
    if args:
        # Override with any CLI flags that were explicitly set
        for key, value in vars(args).items():
            if value is not None and hasattr(config, key):
                setattr(config, key, value)
    return config
```

### Pattern 3: JSON Error Output
**What:** Errors written as JSON to stderr with structured codes and non-zero exit.
**When to use:** All error paths in tools (D-03).
**Example:**
```python
import json
import sys

# Exit codes
EXIT_INVALID_ARG = 2
EXIT_API_ERROR = 3
EXIT_CONFIG_ERROR = 4
EXIT_TRADE_FAILED = 5

def error_exit(message: str, code: str, exit_code: int = 1):
    """Write structured error to stderr and exit."""
    json.dump({"error": message, "code": code}, sys.stderr)
    sys.stderr.write("\n")
    sys.exit(exit_code)
```

### Pattern 4: Paper Trade Pricing (D-09, SAFE-02)
**What:** Paper trades use real orderbook prices -- buys fill at best ask, sells at best bid.
**When to use:** `execute_trade.py` in paper mode.
**Example:**
```python
from py_clob_client.client import ClobClient

def get_paper_fill_price(token_id: str, side: str, host: str) -> float:
    """Get realistic fill price from CLOB API for paper trading.

    CRITICAL: get_price() uses book-side semantics:
    - get_price(token_id, 'BUY') = best bid (highest buy order on book)
    - get_price(token_id, 'SELL') = best ask (lowest sell order on book)

    For paper fills (taker perspective):
    - Paper BUY fills at best ask -> get_price(token_id, 'SELL')
    - Paper SELL fills at best bid -> get_price(token_id, 'BUY')
    """
    reader = ClobClient(host)
    if side == "BUY":
        # Buyer fills at best ask
        result = reader.get_price(token_id, "SELL")
    else:
        # Seller fills at best bid
        result = reader.get_price(token_id, "BUY")

    price = float(result.get("price", 0))
    if price <= 0:
        raise ValueError(f"No {side} price available for token {token_id}")
    return price
```

### Anti-Patterns to Avoid
- **Using mid-price for paper fills:** v1 used `market.yes_price` (mid-price from Gamma). D-09 explicitly requires ask/bid from CLOB API orderbook. Never use midpoint for paper fill simulation.
- **Assuming `get_price('BUY')` returns what buyers pay:** It returns the best bid (what buyers are offering). Takers who want to buy immediately pay the best ask, which is `get_price('SELL')`.
- **Hardcoding minimum order size:** The Gamma API returns `orderMinSize` per market (currently 5 USDC for all observed markets). Read this from the market data, don't hardcode.
- **Ignoring neg-risk:** The py-clob-client handles neg-risk routing automatically in `create_order()` via `get_neg_risk(token_id)`. Don't try to manually select exchange contracts.
- **Creating ClobClient per API call:** For read-only operations (pricing, orderbook), a single unauthenticated `ClobClient(host)` instance can be reused. Only live trading needs authenticated client.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| CLOB API order signing | Custom EIP-712 signing | `py-clob-client.create_order()` + `post_order()` | Complex cryptographic signing with chain-specific parameters. The SDK handles signature types, nonce, fee rates, rounding. |
| Neg-risk market routing | Manual exchange contract selection | `py-clob-client.get_neg_risk(token_id)` (called automatically by `create_order`) | The SDK caches neg-risk status and routes to correct exchange contract. |
| Order amount rounding | Custom decimal rounding | py-clob-client's `ROUNDING_CONFIG` per tick size | Size always 2 decimals, price decimals vary by tick size (1-4). SDK handles all rounding internally. |
| Gamma API JSON parsing | Naive `dict` access | Dataclass with `json.loads()` for stringified fields | `clobTokenIds` and `outcomePrices` are strings containing JSON. Must parse explicitly. v1 has working `_parse_market()`. |
| Dual logging | Custom log routing | Python `logging` module with multiple handlers | v1 `logger_setup.py` already has working console + JSON file handler pattern. |
| Orderbook best bid/ask | Parsing full orderbook | `ClobClient.get_price(token_id, side)` | Returns best price per side directly. Avoids stale orderbook issue (GitHub issue #180). |

**Key insight:** The py-clob-client SDK handles the most dangerous complexity (cryptographic signing, neg-risk routing, decimal rounding). The main hand-rolling risk is paper trade pricing, where the counter-intuitive `get_price` side semantics can produce incorrect fills.

## Common Pitfalls

### Pitfall 1: get_price Side Semantics Are Inverted From Taker Perspective
**What goes wrong:** Calling `get_price(token_id, 'BUY')` and using it as the fill price for a paper BUY order. This gives the best bid (what existing buyers offer), not the best ask (what a new buyer would pay).
**Why it happens:** "BUY" naturally reads as "the price to buy at", but the API uses book-side semantics: "the best price on the BUY side of the book" (i.e., best bid).
**How to avoid:** Paper BUY fills = `get_price(token_id, 'SELL')` (best ask). Paper SELL fills = `get_price(token_id, 'BUY')` (best bid). Document this in code comments.
**Warning signs:** Paper trades showing tighter spread than real market, paper P&L consistently better than expected.

### Pitfall 2: Gamma API Stringified JSON Fields
**What goes wrong:** Treating `clobTokenIds` and `outcomePrices` as native lists when they're actually JSON strings within the JSON response.
**Why it happens:** Most API fields are normal types, but these two are stringified arrays. Easy to miss.
**How to avoid:** Always `json.loads()` these fields. v1's `_parse_market()` already handles this correctly -- cherry-pick that logic.
**Warning signs:** `TypeError` or getting a string instead of a list when accessing token IDs.

### Pitfall 3: Stale Orderbook from get_order_book
**What goes wrong:** `get_order_book()` returns stale data showing 0.01/0.99 spread for active markets.
**Why it happens:** Known issue (GitHub #180) with the `/book` REST endpoint serving disconnected snapshots.
**How to avoid:** Use `get_price(token_id, side)` for best bid/ask instead of parsing `get_order_book()`. The `/price` endpoint serves live data.
**Warning signs:** All markets showing extreme spreads (0.01 bid, 0.99 ask).

### Pitfall 4: Missing CLOB API Error Handling in Paper Mode
**What goes wrong:** Paper trades succeed even when CLOB API is down, because the old code uses Gamma API mid-prices instead of CLOB orderbook.
**Why it happens:** D-10 explicitly requires: "If CLOB API is unreachable during paper trading, the trade fails with a clear error." No fake fills allowed.
**How to avoid:** Paper trade execution must call CLOB API for pricing. If the call fails, the paper trade fails -- don't fall back to Gamma API prices.
**Warning signs:** Paper trades executing during network outages.

### Pitfall 5: Minimum Order Size Violation
**What goes wrong:** Placing orders below the 5 USDC minimum notional (SAFE-05).
**Why it happens:** Kelly criterion can produce small position sizes when edge is marginal. v1 had a $1 minimum which is below the actual exchange minimum.
**How to avoid:** Enforce `orderMinSize` from market data (currently 5 USDC for all markets). Validate `price * size >= 5.0` before any order (paper or live).
**Warning signs:** Live orders rejected by CLOB API with size errors.

### Pitfall 6: Sell Order Size Precision
**What goes wrong:** Sell orders with more than 2 decimal places in size get rejected.
**Why it happens:** SAFE-05 requires "max 2 decimal places for sell orders". The py-clob-client's `ROUNDING_CONFIG` enforces 2 decimal places for `size` across all tick sizes, but tool-level validation should also enforce this.
**How to avoid:** Round size to 2 decimal places (`round_down(size, 2)`) before passing to order creation.
**Warning signs:** Order creation throwing exceptions about invalid size.

## Code Examples

### Example 1: Fetching Markets from Gamma API (verified from v1 + live testing)
```python
# Source: v1 market_discovery.py + live Gamma API response
import json
import requests
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
    best_bid: float        # NEW: from Gamma API bestBid
    best_ask: float        # NEW: from Gamma API bestAsk
    volume_24h: float
    liquidity: float
    end_date: str
    category: str
    active: bool
    closed: bool
    neg_risk: bool         # NEW: INST-09 requirement
    order_min_size: float  # NEW: SAFE-05 requirement
    tick_size: float       # NEW: for price validation

    def to_dict(self) -> dict:
        return asdict(self)

def _parse_market(m: dict) -> Market | None:
    tokens = m.get("clobTokenIds") or m.get("clob_token_ids")
    if not tokens:
        return None
    if isinstance(tokens, str):
        tokens = json.loads(tokens)  # CRITICAL: stringified JSON
    if len(tokens) < 2:
        return None

    outcome_prices = m.get("outcomePrices") or m.get("outcome_prices") or "[]"
    if isinstance(outcome_prices, str):
        outcome_prices = json.loads(outcome_prices)  # CRITICAL: stringified JSON

    yes_price = float(outcome_prices[0]) if outcome_prices else 0.5
    no_price = float(outcome_prices[1]) if len(outcome_prices) > 1 else 0.5

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
```

### Example 2: CLOB API Pricing for Paper Trades (verified live)
```python
# Source: py-clob-client v0.34.6 + live CLOB API testing
from py_clob_client.client import ClobClient

def get_fill_price(token_id: str, trade_side: str, host: str) -> float:
    """Get realistic fill price from CLOB API.

    VERIFIED EMPIRICALLY (2026-03-26):
    - get_price(token, 'BUY')  -> best bid (book-side: highest buy order)
    - get_price(token, 'SELL') -> best ask (book-side: lowest sell order)

    For taker fills:
    - Buying  -> pay best ask -> get_price(token, 'SELL')
    - Selling -> receive best bid -> get_price(token, 'BUY')
    """
    reader = ClobClient(host)

    if trade_side == "BUY":
        result = reader.get_price(token_id, "SELL")  # best ask
    elif trade_side == "SELL":
        result = reader.get_price(token_id, "BUY")   # best bid
    else:
        raise ValueError(f"Invalid side: {trade_side}")

    price = float(result.get("price", 0))
    if price <= 0:
        raise ValueError(f"No liquidity for {trade_side} on token {token_id}")
    return price
```

### Example 3: Kelly Criterion (verified from v1)
```python
# Source: v1 strategy.py (tested, working)
def kelly_criterion(prob: float, odds_price: float, fraction: float = 0.25) -> float:
    """Fractional Kelly criterion for binary outcome.

    Args:
        prob: Estimated true probability of winning
        odds_price: Price per share (payout is 1.0 on win)
        fraction: Kelly fraction (0.25 = quarter Kelly for safety)

    Returns: Fraction of bankroll to bet (0.0 if no edge).
    """
    if odds_price <= 0 or odds_price >= 1:
        return 0.0

    b = (1 - odds_price) / odds_price  # net odds
    q = 1 - prob
    kelly = (b * prob - q) / b
    kelly = max(0.0, kelly)  # no negative bets

    return kelly * fraction
```

### Example 4: Graceful Shutdown Handler (adapted from v1)
```python
# Source: v1 main.py signal handling, adapted for CLI tools
import signal
import sys

_shutdown_requested = False

def _signal_handler(sig, frame):
    global _shutdown_requested
    _shutdown_requested = True

def register_shutdown_handler():
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

def is_shutdown_requested() -> bool:
    return _shutdown_requested
```

### Example 5: Neg-Risk Market Detection (verified live)
```python
# Source: Gamma API live response + py-clob-client source
# Gamma API returns negRisk boolean directly on market objects.
# py-clob-client also has get_neg_risk(token_id) that queries CLOB API.

# For discovery/display: use Gamma API field
market = _parse_market(raw_market)
if market.neg_risk:
    # This market uses NegRisk Exchange contract
    # py-clob-client handles this automatically in create_order()
    pass

# For order creation: py-clob-client auto-detects
# create_order() internally calls get_neg_risk() and routes to correct exchange
signed_order = client.create_order(order_args)  # handles neg-risk automatically
```

## State of the Art

| Old Approach (v1) | Current Approach (v2) | When Changed | Impact |
|-------------------|-----------------------|--------------|--------|
| Mid-price paper fills | Best ask (buy) / best bid (sell) from CLOB API | Phase 1 design decision (D-09) | More realistic paper P&L |
| Monolithic main.py loop | Stateless CLI tools callable by agent | Phase 1 design decision (D-04) | Agent can invoke tools independently |
| Global config module | Config dataclass with CLI override support | Phase 1 design decision (D-08) | Tools can be parameterized per invocation |
| Console print for portfolio | JSON stdout for all output | Phase 1 design decision (D-02) | Machine-parseable output for agent |
| GPT-4o for analysis | Deferred to Phase 2 (agent layer) | Architecture decision | Phase 1 is instrument-only, no AI |
| `openai` SDK dependency | Removed from Phase 1 | Architecture decision | Instrument layer has no AI dependency |

**Deprecated/outdated:**
- v1 `market_analyzer.py`: Uses OpenAI SDK. Not needed in Phase 1.
- v1 `main.py` loop: Replaced by individual CLI tools. The loop pattern moves to the agent layer (Phase 2).

## Open Questions

1. **SQLite Schema: Evolve or Fresh?**
   - What we know: v1 has a 5-table schema (trades, positions, decisions, market_snapshots, strategy_metrics) that works well. Tests verify it.
   - What's unclear: Should we add new columns (neg_risk, tick_size, best_bid, best_ask to trades/positions) or keep the v1 schema exactly?
   - Recommendation: **Adapt the v1 schema** -- add `neg_risk BOOLEAN DEFAULT 0` and `fill_price REAL` (the actual orderbook price at fill time, separate from limit price) to the trades table. This preserves compatibility while supporting new D-09 auditing needs. All new fields should have defaults so existing data stays valid.

2. **Edge Calculation Tool: External Probability Input?**
   - What we know: INST-03 says "calculates edge (estimated probability - market price)". In v2, probability estimation is done by the agent (Phase 2), not the instrument layer.
   - What's unclear: Should the edge calculation tool accept `--estimated-prob` as a CLI argument?
   - Recommendation: **Yes** -- the tool takes `--market-id` and `--estimated-prob` as inputs, fetches current market price from CLOB API, returns edge and Kelly sizing. Pure calculation, no AI.

3. **Gamma API Rate Limits**
   - What we know: STATE.md flags "Gamma API rate limits not documented -- may need empirical testing". Live testing showed no issues fetching markets.
   - What's unclear: Exact rate limits, whether they apply per-endpoint or globally.
   - Recommendation: Include reasonable request timeouts (30s) and retry with backoff on 429 responses. Don't parallelize Gamma API calls in Phase 1 (tools are single-purpose, sequential).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.12 | All code | Yes | 3.12.9 | -- |
| pip | Package management | Yes | 24.3.1 | -- |
| virtualenv (.venv) | Isolation | Yes | Active | -- |
| py-clob-client | INST-02, INST-05, INST-06, INST-09 | Yes | 0.34.6 | -- |
| requests | INST-01 (Gamma API) | Yes | 2.32.5 | -- |
| python-dotenv | INST-11 (config) | Yes | 1.2.2 | -- |
| eth-account | INST-06 (live trading) | Yes | 0.13.7 | Paper mode works without it |
| web3 | setup_wallet.py only | Yes | 7.14.1 | -- |
| pytest | Testing | Yes | 9.0.2 | -- |
| SQLite3 | INST-10 (persistence) | Yes | stdlib | -- |
| Gamma API | INST-01 (market data) | Yes (verified live) | -- | -- |
| CLOB API | INST-02, INST-05 (pricing) | Yes (verified live) | -- | -- |

**Missing dependencies with no fallback:** None.

**Missing dependencies with fallback:** None.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None -- see Wave 0 |
| Quick run command | `python -m pytest tests/ -x -q --timeout=30` |
| Full suite command | `python -m pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INST-01 | Market discovery returns filtered JSON list | integration | `python -m pytest tests/test_market_data.py -x` | No -- Wave 0 |
| INST-02 | Orderbook prices fetched from CLOB API | integration | `python -m pytest tests/test_pricing.py -x` | No -- Wave 0 |
| INST-03 | Edge calculation returns correct value | unit | `python -m pytest tests/test_kelly.py::test_edge_calculation -x` | No -- Wave 0 |
| INST-04 | Kelly criterion sizing is correct | unit | `python -m pytest tests/test_kelly.py::test_kelly_criterion -x` | No -- Wave 0 |
| INST-05 | Paper trade fills at best ask (buy) / best bid (sell) | integration | `python -m pytest tests/test_trading.py::test_paper_fill_pricing -x` | No -- Wave 0 |
| INST-06 | Live trade creates signed GTC order via py-clob-client | unit (mocked) | `python -m pytest tests/test_trading.py::test_live_trade -x` | No -- Wave 0 |
| INST-07 | Portfolio shows open positions with unrealized P&L | unit | `python -m pytest tests/test_portfolio.py::test_portfolio_summary -x` | No -- Wave 0 |
| INST-08 | Resolved markets detected and P&L finalized | unit | `python -m pytest tests/test_portfolio.py::test_resolved_markets -x` | No -- Wave 0 |
| INST-09 | Neg-risk markets identified and handled | integration | `python -m pytest tests/test_market_data.py::test_neg_risk_detection -x` | No -- Wave 0 |
| INST-10 | SQLite stores all data types correctly | unit | `python -m pytest tests/test_db.py -x` | No -- Wave 0 |
| INST-11 | Config loads from .env with CLI overrides | unit | `python -m pytest tests/test_config.py -x` | No -- Wave 0 |
| INST-12 | SIGINT handled gracefully | unit | `python -m pytest tests/test_cli.py::test_sigint_handling -x` | No -- Wave 0 |
| INST-13 | Dual logging (console + JSON file) | unit | `python -m pytest tests/test_config.py::test_logging -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q --timeout=30`
- **Per wave merge:** `python -m pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/conftest.py` -- shared fixtures (temp DB, mock config, mock CLOB client)
- [ ] `tests/test_config.py` -- config loading and CLI override tests (INST-11, INST-13)
- [ ] `tests/test_market_data.py` -- Gamma API integration (INST-01, INST-09)
- [ ] `tests/test_pricing.py` -- CLOB API pricing (INST-02)
- [ ] `tests/test_kelly.py` -- Kelly criterion and edge (INST-03, INST-04)
- [ ] `tests/test_trading.py` -- paper/live trade execution (INST-05, INST-06)
- [ ] `tests/test_portfolio.py` -- portfolio and resolved markets (INST-07, INST-08)
- [ ] `tests/test_db.py` -- SQLite persistence (INST-10)
- [ ] `tests/test_cli.py` -- CLI argument parsing, error output, SIGINT (INST-12)
- [ ] `pytest.ini` or `pyproject.toml [tool.pytest]` -- pytest configuration

## Project Constraints (from CLAUDE.md)

Directives extracted from CLAUDE.md that constrain implementation:

- **Python 3.12** -- all source code
- **Virtual environment at `.venv/`** -- must activate before running
- **Always run tests after changes** -- `python tests/test_paper_trading.py` (will need updating for new structure)
- **Never commit** `.env`, `trading.db`, `trading.log`, or `.claude/`
- **Paper trading is default** -- never change `PAPER_TRADING` to `false` without explicit user request
- **Keep modules flat** -- v1 convention was flat root, but D-05 explicitly moves to `tools/` + `lib/` structure
- **All parameters in config** -- no hardcoded values in other modules
- **Secrets only in `.env`** -- loaded via `python-dotenv`, never in source code
- **signature_type = 0** -- EOA wallets use type 0 (not 1)
- **Stringified JSON fields** -- `clobTokenIds` and `outcomePrices` require `json.loads()`
- **Kelly fraction = 0.25** -- quarter Kelly default
- **GTC limit orders** -- not FOK or market orders
- **Neg-risk exchange = `0xC5d563A36AE78145C45a50134d48A1215220f80a`** -- separate contract
- **Token allowances for both Exchange AND NegRisk Exchange** -- USDC approve + CTF setApprovalForAll

## Sources

### Primary (HIGH confidence)
- **py-clob-client v0.34.6** (installed, source inspected) -- `get_price()`, `get_order_book()`, `create_order()`, `OrderBookSummary`, `ROUNDING_CONFIG`, `TickSize`, `get_neg_risk()` all verified from source code
- **CLOB API live testing** (2026-03-26) -- `get_price(token_id, 'BUY')` = best bid, `get_price(token_id, 'SELL')` = best ask, verified across multiple markets
- **Gamma API live testing** (2026-03-26) -- Market response fields verified: `negRisk`, `bestBid`, `bestAsk`, `orderMinSize`, `orderPriceMinTickSize` all present
- **v1 source code** (all 10 .py files read) -- Working implementations of all core functions

### Secondary (MEDIUM confidence)
- [Polymarket CLOB public methods docs](https://docs.polymarket.com/developers/CLOB/clients/methods-public) -- Method signatures and descriptions
- [Polymarket neg-risk overview](https://docs.polymarket.com/developers/neg-risk/overview) -- Neg-risk mechanism and contract routing
- [py-clob-client GitHub](https://github.com/Polymarket/py-clob-client) -- README and issue tracker

### Tertiary (LOW confidence)
- [py-clob-client issue #180](https://github.com/Polymarket/py-clob-client/issues/180) -- Known stale orderbook issue (reported by users, acknowledged by maintainers)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all packages already installed and verified, no new dependencies needed
- Architecture: HIGH -- clear user decisions (D-01 through D-11), v1 code provides proven implementations to cherry-pick
- Pitfalls: HIGH -- `get_price` side semantics, stringified JSON, stale orderbook all verified empirically with live API calls
- API integration: HIGH -- both Gamma API and CLOB API tested live on 2026-03-26

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- Polymarket APIs and py-clob-client are mature)
