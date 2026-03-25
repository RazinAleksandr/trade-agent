# Architecture

## Overview

The agent follows a linear pipeline architecture. Each cycle executes the same sequence of steps, orchestrated by `main.py`. All modules are flat (no sub-packages) and communicate through well-defined data structures.

## Data Flow

```
main.py (orchestrator)
  │
  ├── market_discovery.fetch_active_markets()
  │   └── Gamma API → list[Market]
  │
  ├── data_store.record_market_snapshot()
  │   └── Persists price/volume data for each market
  │
  ├── market_analyzer.batch_analyze()
  │   ├── OpenAI GPT-4o (+ web search)
  │   └── → list[MarketAnalysis]
  │
  ├── strategy.generate_signals()
  │   ├── Kelly criterion sizing
  │   └── → list[TradeSignal]
  │
  ├── trader.execute_signal()
  │   ├── Paper mode → simulate + record in SQLite
  │   └── Live mode → py-clob-client → Polymarket CLOB
  │
  ├── portfolio.update_position_prices()
  │   └── Fetches current prices for open positions
  │
  ├── portfolio.check_for_resolved_markets()
  │   └── Closes positions on resolved markets, calculates realized P&L
  │
  └── portfolio.check_risk_limits()
      └── Warns if exposure approaches limits
```

## Module Responsibilities

### `config.py`
Single source of truth for all parameters. Loads from `.env` via `python-dotenv`. No logic — just variable definitions.

### `market_discovery.py`
Talks to Polymarket's Gamma API. Fetches active markets, parses the response (handling stringified JSON fields), and filters by volume, liquidity, and price range. Exports the `Market` dataclass used throughout the system.

### `market_analyzer.py`
Sends market data to OpenAI GPT-4o with a structured prompt. Optionally enables web search so the model can look up latest news/polls. Parses the JSON response into `MarketAnalysis`. Runs up to 4 analyses in parallel via `ThreadPoolExecutor`.

### `strategy.py`
Takes analyses and converts them into actionable `TradeSignal`s. Uses fractional Kelly criterion (quarter Kelly by default) for position sizing. Filters by minimum edge threshold and available capital. Avoids doubling up on existing positions.

### `trader.py`
Executes signals. In paper mode, generates a UUID order ID and records the trade in SQLite. In live mode, creates and signs an order via `py-clob-client` and posts it to Polymarket's CLOB as a GTC limit order.

### `portfolio.py`
Reads positions from the database, fetches current market prices, and calculates unrealized P&L. Detects resolved markets and closes positions. Enforces risk limits (total exposure, per-position size).

### `data_store.py`
SQLite wrapper. Manages five tables: `trades`, `positions`, `decisions`, `market_snapshots`, `strategy_metrics`. Handles position upserts with cost averaging.

### `logger_setup.py`
Dual-output logging: human-readable to console, structured JSON to file (`trading.log`). Provides `log_decision()` for structured strategy event logging.

### `setup_wallet.py`
One-time interactive script. Generates or imports a wallet, derives Polymarket L2 API credentials, and sets token allowances on Polygon for both exchange contracts.

### `main.py`
Entry point. Validates config, initializes all components, runs the trading loop with graceful shutdown (SIGINT/SIGTERM). Runs strategy review every 5 cycles.

## Data Structures

### `Market` (market_discovery.py)
```python
@dataclass
class Market:
    id: str               # Polymarket market ID
    condition_id: str      # On-chain condition ID
    question: str          # "Will X happen by Y?"
    description: str       # Full market description
    yes_token_id: str      # CLOB token ID for YES outcome
    no_token_id: str       # CLOB token ID for NO outcome
    yes_price: float       # Current YES price (0.0–1.0)
    no_price: float        # Current NO price (0.0–1.0)
    volume_24h: float      # 24h volume in USDC
    liquidity: float       # Available liquidity in USDC
    end_date: str          # Resolution date
    category: str          # Market category
    active: bool
    closed: bool
```

### `MarketAnalysis` (market_analyzer.py)
```python
@dataclass
class MarketAnalysis:
    market_id: str
    question: str
    market_price: float      # Current YES price
    estimated_prob: float    # Our estimated true probability
    confidence: float        # 0.0–1.0
    edge: float              # estimated_prob - market_price
    reasoning: str           # 2-3 sentence explanation
    key_factors: list[str]
    information_edge: str    # What the market might be missing
    raw_response: dict       # Full parsed JSON from OpenAI
    sources: list[str]       # URLs consulted
```

### `TradeSignal` (strategy.py)
```python
@dataclass
class TradeSignal:
    market_id: str
    question: str
    side: str             # "YES" or "NO"
    token_id: str         # CLOB token ID to trade
    price: float          # Limit price
    size: float           # Number of shares
    cost_usdc: float      # Total cost
    edge: float
    kelly_raw: float      # Full Kelly fraction
    kelly_adjusted: float # After applying KELLY_FRACTION
    confidence: float
    reasoning: str
```

### `OrderResult` (trader.py)
```python
@dataclass
class OrderResult:
    order_id: str
    success: bool
    message: str
    is_paper: bool
```

## Database Schema

Five tables in SQLite (`trading.db`):

| Table | Purpose |
|---|---|
| `trades` | Every executed trade (paper or live) |
| `positions` | Currently open and historically closed positions |
| `decisions` | Logged strategy decisions with metadata |
| `market_snapshots` | Point-in-time market data for analysis |
| `strategy_metrics` | Periodic performance summaries |

See `data_store.py:_create_tables()` for full column definitions.

## Main Loop Lifecycle

```
┌─────────────────────────────────────┐
│         Startup                     │
│  - Validate config (API key, etc)   │
│  - Init DataStore, Trader, Portfolio│
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│      CYCLE N (run_trading_cycle)    │◄──────────┐
│                                     │           │
│  1. Discover markets (Gamma API)    │           │
│  2. Snapshot prices to SQLite       │           │
│  3. Analyze with OpenAI (parallel)  │           │
│  4. Generate trade signals (Kelly)  │           │
│  5. Execute paper/live trades       │           │
│  6. Update portfolio & check risk   │           │
│                                     │           │
│  Print portfolio summary            │           │
│  Every 5th cycle: strategy review   │           │
└──────────────┬──────────────────────┘           │
               │                                  │
               ▼                                  │
┌─────────────────────────────────────┐           │
│  Sleep 300 seconds (5 min)          │           │
│  (checks every 1s for shutdown)     │───────────┘
└──────────────┬──────────────────────┘
               │ Ctrl+C or SIGTERM
               ▼
┌─────────────────────────────────────┐
│  Graceful Shutdown                  │
│  - Final portfolio summary          │
│  - Strategy update                  │
│  - Close database                   │
└─────────────────────────────────────┘
```

### Key behaviors

- **Runs forever.** The `while not shutdown_requested` loop repeats until Ctrl+C or SIGTERM.
- **Interruptible sleep.** Instead of one `time.sleep(300)`, it sleeps 1 second at a time, checking the shutdown flag each second. Ctrl+C responds within 1 second, not after 5 minutes.
- **Errors don't crash the loop.** If market discovery or analysis fails, that cycle returns early and the next cycle starts normally. Individual trade failures are logged and skipped.
- **State accumulates.** The SQLite database persists across cycles — positions from cycle 1 are still tracked in cycle 50. The strategy module checks existing positions to avoid doubling up on the same market.
- **Strategy review every 5 cycles (~25 min).** Calculates win rate, total P&L, and average edge from the database and logs a performance summary.

## Concurrency

- **Market analysis** runs in parallel via `ThreadPoolExecutor(max_workers=4)`
- Everything else is sequential within a cycle
- The main loop is single-threaded with a sleep between cycles
- Graceful shutdown via `signal.SIGINT`/`signal.SIGTERM` handlers
