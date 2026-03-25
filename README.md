# Polymarket Autonomous Trading Agent

Fully autonomous prediction market trading agent for [Polymarket](https://polymarket.com). Discovers markets, analyzes them with OpenAI GPT-4o (with web search), calculates edge using Kelly criterion, sizes positions, executes trades, and monitors portfolio — all in a continuous loop.

**Paper trading by default.** No real money at risk until you explicitly switch to live mode.

## Quick Start

```bash
# 1. Clone and set up
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt  # or: pip install anthropic py-clob-client python-dotenv web3 eth-account openai

# 2. Configure
cp .env.example .env
# Edit .env — add your OPENAI_API_KEY

# 3. Run (paper trading)
python main.py
```

## How It Works

Each cycle (every 5 minutes by default):

1. **Discover** — Fetches active markets from Polymarket's Gamma API, filters by volume and liquidity
2. **Analyze** — Sends each market to GPT-4o with web search for true probability estimation
3. **Signal** — Compares estimated probability vs market price, filters by minimum edge (10%)
4. **Size** — Uses quarter-Kelly criterion for conservative position sizing
5. **Execute** — Places GTC limit orders (paper or live via CLOB API)
6. **Monitor** — Tracks positions, updates P&L, detects resolved markets, checks risk limits

## Project Structure

```
polymarket-agent/
  config.py              # All parameters (loaded from .env)
  market_discovery.py    # Gamma API integration, market filtering
  market_analyzer.py     # OpenAI GPT-4o analysis with web search
  strategy.py            # Kelly criterion sizing, signal generation
  trader.py              # Paper + live trade execution
  portfolio.py           # Position tracking, P&L, risk limits
  data_store.py          # SQLite persistence
  logger_setup.py        # Structured JSON logging
  setup_wallet.py        # One-time wallet & credential setup
  main.py                # Entry point — autonomous trading loop
  tests/
    test_paper_trading.py
  docs/                  # Detailed documentation
    architecture.md      # System architecture & data flow
    configuration.md     # All config parameters & .env setup
    trading-engine.md    # Strategy, sizing, and execution details
    api-reference.md     # External APIs (Gamma, CLOB, OpenAI)
    wallet-setup.md      # Wallet generation & live trading setup
    testing.md           # Running and writing tests
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System design, data flow, module responsibilities |
| [Configuration](docs/configuration.md) | Environment variables, defaults, .env setup |
| [Trading Engine](docs/trading-engine.md) | Kelly criterion, signal generation, paper vs live execution |
| [API Reference](docs/api-reference.md) | Gamma API, CLOB API, OpenAI integration details |
| [Wallet Setup](docs/wallet-setup.md) | Wallet generation, API credentials, token allowances |
| [Testing](docs/testing.md) | Running tests, test coverage, adding new tests |

## Key Configuration

| Parameter | Default | Description |
|---|---|---|
| `OPENAI_API_KEY` | — | **Required.** OpenAI API key |
| `PAPER_TRADING` | `true` | Paper mode (no real orders) |
| `MIN_EDGE_THRESHOLD` | `0.10` | Minimum 10% edge to trade |
| `KELLY_FRACTION` | `0.25` | Quarter Kelly (conservative sizing) |
| `MAX_POSITION_SIZE_USDC` | `50` | Max per-position size |
| `MAX_TOTAL_EXPOSURE_USDC` | `200` | Max total portfolio exposure |
| `LOOP_INTERVAL` | `300` | Seconds between cycles |

See [Configuration](docs/configuration.md) for the full list.

## Paper Trading vs Live Trading

**Paper trading** (default) uses real market data and real OpenAI analysis but simulates order execution. Trades are recorded locally in SQLite. Good for validating strategy before risking real money.

**Live trading** requires a funded Polygon wallet with MATIC (gas) and USDC. See [Wallet Setup](docs/wallet-setup.md).

```bash
# Switch to live (after wallet setup)
# In .env:
PAPER_TRADING=false
```

## Running Tests

```bash
source .venv/bin/activate
python tests/test_paper_trading.py
```

## License

Private — not for redistribution.
