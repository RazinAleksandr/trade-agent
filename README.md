# Polymarket Autonomous Trading Agent

An autonomous prediction market trading agent for [Polymarket](https://polymarket.com). Built as a two-layer system:

1. **Instrument Layer** (Python) -- Stateless CLI tools for market data, order execution, and portfolio tracking
2. **Agent Layer** (Claude Code) -- Multi-agent system that discovers markets, estimates probabilities, sizes positions, executes trades, and evolves its own strategy over time

The agent starts with zero knowledge. After each trading cycle, it reviews its decisions, extracts learnings, and updates its strategy document -- like a human analyst building a playbook from experience.

Paper trading is the default. Live trading requires explicit setup and safety gates.

## Prerequisites

- Python 3.12+
- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code) (`npm install -g @anthropic-ai/claude-code`)
- An Anthropic API key (for Claude Code)
- tmux (for autonomous scheduled operation)
- cron (for scheduled cycles)
- Internet access (Polymarket APIs, web search for analysis)

## Setup

```bash
# Clone and enter directory
git clone <repo-url>
cd polymarket-agent

# Create and activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create configuration
cp .env.example .env
# Edit .env -- no API keys needed for paper trading with default settings
```

## Quick Start: Run a Trading Cycle

A trading cycle is the core operation. The main Claude agent orchestrates 6 sub-agents in sequence:

```
Strategy Read -> Scanner -> Analyst -> Risk Manager -> Planner -> Execute -> Reviewer -> Strategy Update
```

### Run manually

```bash
# Single cycle in a tmux session (runs unattended)
./run_cycle.sh

# Or interactively in your terminal
source .venv/bin/activate
claude --dangerously-skip-permissions
# Then type: run a trading cycle
```

This will:
1. Read the current strategy (`state/strategy.md`) and core principles
2. **Position Monitor** checks open positions for sells/holds
3. **Scanner** discovers active markets from Polymarket's Gamma API
4. **Analyst** deep-dives each market (web search, Bull/Bear debate, probability estimate)
5. **Risk Manager** sizes positions using Kelly criterion, checks exposure limits, detects correlated markets
6. **Planner** creates a concrete trade plan based on strategy rules + all analysis
7. **Execute** runs paper trades via the instrument layer tools
8. **Reviewer** analyzes results, writes a cycle report to `state/reports/`
9. **Strategy Updater** incrementally updates `state/strategy.md` based on learnings

Each cycle produces structured JSON files in `state/cycles/{cycle_id}/` and a human-readable report in `state/reports/`.

### Run on a schedule

```bash
# Run every 1 hour for 12 hours (overnight sprint)
./schedule_trading.sh start --every 1h --for 12h

# Run every 4 hours for 7 days
./schedule_trading.sh start --every 4h --for 7d

# Check current schedule
./schedule_trading.sh status

# Stop early (current cycle finishes, no new ones start)
./schedule_trading.sh stop
```

Supported frequencies: `1h`, `2h`, `4h`, `6h`, `8h`, `12h`. Duration can be hours (`12h`) or days (`7d`).

Each cycle runs in its own tmux session. To watch a running cycle:

```bash
tmux ls                          # List sessions
tmux attach -t trading-HHMMSS    # Attach to a session (Ctrl+B, D to detach)
```

Under the hood, `schedule_trading.sh` installs a cron job that calls `run_cycle.sh`. The run script handles PID-based locking (prevents overlapping cycles), auto-stop after the duration expires, and logging to `logs/`.

### Run on a remote server

```bash
# 1. Clone and set up as usual (see Setup above)

# 2. Ensure Claude Code CLI is authenticated
claude --version  # Verify it's installed
# If not yet authenticated, run `claude` once interactively to log in

# 3. (Optional) Create .cron-env if claude is not on the default PATH
echo 'export PATH="/usr/local/bin:/home/user/.npm-global/bin:$PATH"' > .cron-env

# 4. Start the schedule
./schedule_trading.sh start --every 1h --for 24h

# 5. Detach and leave it running
# The cron job + tmux handles everything. SSH back anytime to check:
./schedule_trading.sh status
ls -la state/reports/            # Cycle reports
ls -la logs/                     # Session logs
```

The `--dangerously-skip-permissions` flag is used automatically by `run_cycle.sh` so Claude can execute tools without interactive approval. This is required for unattended operation.

## CLI Tools

All tools output JSON to stdout. Add `--pretty` for human-readable formatting.

### Market Discovery

```bash
# Find active, tradable markets
python tools/discover_markets.py --pretty

# With filters
python tools/discover_markets.py --min-volume 5000 --min-liquidity 1000 --limit 5 --pretty
```

### Pricing

```bash
# Get orderbook prices for a token
python tools/get_prices.py --token-id <CLOB_TOKEN_ID> --pretty
```

### Edge & Position Sizing

```bash
# Calculate edge (your estimate vs market price)
python tools/calculate_edge.py --estimated-prob 0.70 --market-price 0.55 --pretty

# Calculate Kelly criterion position size
python tools/calculate_kelly.py --estimated-prob 0.70 --market-price 0.55 --bankroll 200 --pretty
```

### Trade Execution

```bash
# Paper trade (default)
python tools/execute_trade.py \
  --market-id <MARKET_ID> \
  --token-id <TOKEN_ID> \
  --side YES \
  --size 10 \
  --pretty

# Live trade (requires gate pass + PAPER_TRADING=false)
python tools/execute_trade.py \
  --market-id <MARKET_ID> \
  --token-id <TOKEN_ID> \
  --side YES \
  --size 10 \
  --price 0.55 \
  --live \
  --pretty
```

### Portfolio

```bash
# View open positions and P&L
python tools/get_portfolio.py --pretty

# Include risk limit warnings
python tools/get_portfolio.py --include-risk --pretty

# Check for resolved markets (finalizes P&L)
python tools/check_resolved.py --pretty
```

## Strategy Evolution

The agent builds its own trading strategy from scratch:

- **`state/strategy.md`** -- Evolving strategy document with 4 domains: market selection rules, analysis approach, risk parameters, trade entry/exit rules. Updated by the Strategy Updater after each cycle (1-3 changes max).
- **`state/core-principles.md`** -- Human-set principles that the agent reads but never modifies. Edit this file to set guardrails.
- **`state/reports/`** -- Per-cycle markdown reports with full trade analysis, reasoning, and learnings.

The strategy starts blank. Over many cycles, it develops into a comprehensive playbook based on what the agent observes working (and not working) in paper trading.

## Live Trading

Live trading has multiple safety gates:

### 1. Set up wallet

```bash
python setup_wallet.py
```

This generates (or imports) an Ethereum wallet, derives L2 API credentials for Polymarket's CLOB, and sets token allowances on Polygon. You'll need to fund the wallet with MATIC (gas) and USDC (trading capital).

### 2. Pass the live trading gate

```bash
# Check if you qualify
python tools/enable_live.py --status

# Enable live trading (interactive -- requires positive paper P&L over 10+ cycles)
python tools/enable_live.py
```

The gate requires:
- Minimum 10 paper trading cycles completed (configurable via `MIN_PAPER_CYCLES`)
- Positive aggregate paper P&L across those cycles
- Typing "CONFIRM LIVE" to proceed

This creates a `.live-gate-pass` file. To revoke: `python tools/enable_live.py --revoke`

### 3. Switch to live mode

```env
# In .env
PAPER_TRADING=false
PRIVATE_KEY=your_ethereum_private_key
```

## Configuration

All parameters are in `.env`. See `.env.example` for the full list.

| Parameter | Default | Description |
|---|---|---|
| `PAPER_TRADING` | `true` | Paper mode (no real orders) |
| `MIN_EDGE_THRESHOLD` | `0.10` | Minimum 10% edge to trade |
| `KELLY_FRACTION` | `0.25` | Quarter Kelly for conservative sizing |
| `MAX_POSITION_SIZE_USDC` | `50` | Max single position in USDC |
| `MAX_TOTAL_EXPOSURE_USDC` | `200` | Max portfolio exposure in USDC |
| `MIN_VOLUME_24H` | `1000` | Min 24h volume filter |
| `MIN_LIQUIDITY` | `500` | Min liquidity filter |
| `MAX_MARKETS_PER_CYCLE` | `10` | Max markets per cycle |
| `CYCLE_INTERVAL` | `4h` | Schedule interval (30m, 1h, 4h, 6h, 12h, 1d) |
| `MIN_PAPER_CYCLES` | `10` | Cycles before live gate opens |
| `DB_PATH` | `trading.db` | SQLite database path |
| `LOG_LEVEL` | `INFO` | Logging verbosity |
| `LOG_FILE` | `trading.log` | Structured JSON log file |

## Project Structure

```
polymarket-agent/
  lib/                    # Python library modules
    config.py             # Configuration loading from .env
    models.py             # Market, TradeSignal, OrderResult dataclasses
    market_data.py        # Gamma API client (market discovery)
    pricing.py            # CLOB API orderbook pricing
    strategy.py           # Kelly criterion, edge calculation, position sizing
    trading.py            # Paper and live trade execution
    portfolio.py          # Position tracking, P&L, risk limits
    db.py                 # SQLite persistence (5 tables)
    agent_schemas.py      # JSON schema validation for sub-agent outputs
    logging_setup.py      # Dual logging (console + JSON file)
    signals.py            # Graceful shutdown (SIGINT/SIGTERM)
    errors.py             # Structured error output
    cycle_state.py        # Cycle ID generation, state management
  tools/                  # CLI tools (JSON output to stdout)
    discover_markets.py   # Find active markets
    get_prices.py         # Orderbook bid/ask prices
    calculate_edge.py     # Edge calculation
    calculate_kelly.py    # Kelly criterion sizing
    execute_trade.py      # Paper and live trade execution
    get_portfolio.py      # Portfolio and P&L
    check_resolved.py     # Resolved market detection
    enable_live.py        # Live trading gate
    setup_schedule.py     # Cron job management
  .claude/agents/         # Claude Code sub-agent definitions
    trading-cycle.md      # Main orchestrator (runs the full pipeline)
    scanner.md            # Market discovery agent
    analyst.md            # Probability estimation (Bull/Bear debate)
    risk-manager.md       # Kelly sizing, correlation detection
    planner.md            # Trade plan generation
    reviewer.md           # Cycle analysis and reporting
    strategy-updater.md   # Strategy evolution
  state/                  # Runtime state (evolves over time)
    strategy.md           # Agent-maintained trading strategy
    core-principles.md    # Human-set principles (read-only for agents)
    cycles/               # Per-cycle JSON data
    reports/              # Per-cycle markdown reports
  tests/                  # Pytest test suite
  setup_wallet.py         # One-time wallet setup for live trading
  schedule_trading.sh     # Start/stop/status for scheduled trading
  run_cycle.sh            # Single cycle runner (tmux + PID locking)
  .env.example            # Configuration template
  requirements.txt        # Python dependencies
```

## Running Tests

```bash
source .venv/bin/activate
pytest tests/ -v
```

## How It Works

The system is designed like a trading desk:

- **Scanner** is the market screener -- finds what's worth looking at
- **Analyst** is the research analyst -- does deep dives with web search, runs Bull/Bear debates
- **Risk Manager** is the risk desk -- checks portfolio limits, sizes positions, flags correlated bets
- **Planner** is the portfolio manager -- decides which trades to actually make, applying strategy rules
- **Reviewer** is the performance analyst -- evaluates what happened and extracts lessons
- **Strategy Updater** is the CIO -- incrementally refines the firm's investment philosophy

Each agent outputs structured JSON that the next agent consumes. The main `trading-cycle` agent orchestrates the pipeline and handles trade execution directly.

Over time, `state/strategy.md` evolves from an empty document into a comprehensive trading playbook -- entirely written by the agent based on its own experience.

## Safety

- Paper trading is always the default
- Live trading requires positive paper P&L over 10+ cycles, plus manual confirmation
- Orders are validated (min 5 USDC, max 2 decimal places, price in 0-1 range)
- CLOB API credentials auto-refresh on 401 errors
- PID lockfile prevents overlapping cycles
- Each sub-agent has a `maxTurns` limit to prevent token cost runaway
- All decisions are logged to SQLite and cycle reports for full auditability
