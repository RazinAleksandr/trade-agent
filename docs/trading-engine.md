# Trading Engine

## Overview

The trading engine has three stages: **analysis** (estimate true probabilities), **strategy** (generate sized trade signals), and **execution** (paper or live orders).

## Market Analysis

**File:** `market_analyzer.py`

Each market is sent to OpenAI GPT-4o with a structured prompt asking the model to:
1. Search the web for latest news, polls, and data
2. Estimate the true probability of the outcome
3. Assess confidence in the estimate
4. Identify what the market might be missing

The model returns a JSON response with:
- `estimated_probability` (0.0–1.0)
- `confidence` (0.0–1.0)
- `reasoning` (2-3 sentences)
- `key_factors` (list of driving factors)
- `information_edge` (what the market may be over/underweighting)
- `sources_consulted` (URLs or source descriptions)

**Web search** is enabled by default (`ENABLE_WEB_SEARCH=true`), giving the model access to real-time information via OpenAI's `web_search` tool (Responses API).

**Parallel execution:** Up to 4 markets are analyzed concurrently via `ThreadPoolExecutor`.

## Edge Calculation

```
edge = estimated_probability - market_price
```

- Positive edge → YES is underpriced (model thinks outcome is more likely than market implies)
- Negative edge → YES is overpriced (model thinks outcome is less likely)

A signal is only generated if:
- `abs(edge) >= MIN_EDGE_THRESHOLD` (default: 10%)
- `abs(edge) * confidence >= MIN_EDGE_THRESHOLD * 0.5` (confidence-weighted check)

## Kelly Criterion Position Sizing

**File:** `strategy.py`

The [Kelly criterion](https://en.wikipedia.org/wiki/Kelly_criterion) determines optimal bet size based on edge and odds:

```
b = (1 - price) / price       # net odds (payout per dollar risked)
kelly = (b * prob - q) / b     # where q = 1 - prob
adjusted = kelly * KELLY_FRACTION
```

The agent uses **quarter Kelly** (`KELLY_FRACTION=0.25`) by default. This is deliberately conservative — full Kelly maximizes long-run growth but with extreme variance. Quarter Kelly sacrifices ~25% of expected growth for much smoother equity curves.

### Position sizing

```
raw_size = adjusted_kelly * available_capital
capped_size = min(raw_size, MAX_POSITION_SIZE_USDC)
shares = capped_size / price
```

### Filters applied
1. No existing position in the same market (no double-dipping)
2. Sufficient remaining capital (respects `MAX_TOTAL_EXPOSURE_USDC`)
3. Kelly suggests positive allocation

## Signal Direction

| Condition | Action |
|---|---|
| `edge > 0` (YES underpriced) | BUY YES tokens at current YES price |
| `edge < 0` (YES overpriced) | BUY NO tokens at current NO price |

The agent always buys the side it believes in — it never sells or shorts.

## Trade Execution

**File:** `trader.py`

### Paper Mode (default)

- Generates a UUID-based order ID (`paper-{hex12}`)
- Records the trade in SQLite immediately
- Updates the position (creates new or averages into existing)
- Assumes instant fill at the specified price
- No slippage, no fees, no partial fills

### Live Mode

- Creates a signed order via `py-clob-client`:
  ```python
  OrderArgs(token_id=token_id, price=price, size=size, side=BUY)
  signed = client.create_order(order_args)
  client.post_order(signed, OrderType.GTC)
  ```
- **GTC (Good-Till-Cancelled):** The order stays on the book until filled or manually cancelled. Better price execution than market orders.
- Records trade and updates position only after successful submission
- Falls back to paper mode if the CLOB client fails to initialize

### Paper vs Live: Key Differences

| Aspect | Paper | Live |
|---|---|---|
| Order placement | Simulated | Real CLOB API |
| Fill assumption | Instant at limit price | Depends on orderbook depth |
| Slippage | None | Real |
| Fees | None | Polymarket trading fees apply |
| Partial fills | Never | Possible |
| Capital at risk | None | Real USDC |

## Portfolio Management

**File:** `portfolio.py`

### Position Tracking
- Positions are stored in SQLite with cost averaging
- When adding to an existing position: `new_avg = (old_cost + new_cost) / (old_size + new_size)`

### Price Updates
- Each cycle fetches current market prices for open positions
- Calculates unrealized P&L: `(current_price - avg_price) * size`

### Market Resolution
- Checks if any open positions are on resolved (closed) markets
- Closes positions using the final market price
- Calculates realized P&L

### Risk Limits
- Warns if total exposure exceeds 90% of `MAX_TOTAL_EXPOSURE_USDC`
- Warns if any single position exceeds 90% of `MAX_POSITION_SIZE_USDC`
- Does not auto-liquidate — warnings only

## Strategy Review

Every 5 cycles, `main.py` calls `run_strategy_update()` which:
1. Pulls aggregate stats from the database (total trades, win rate, P&L, average edge)
2. Records a snapshot in `strategy_metrics` table
3. Logs a summary for monitoring
