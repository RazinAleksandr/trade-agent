# Configuration

All configuration is managed through environment variables, loaded from `.env` by `config.py` via `python-dotenv`.

## Setup

```bash
cp .env.example .env
# Edit .env with your values
```

## Environment Variables

### Required

| Variable | Example | Description |
|---|---|---|
| `OPENAI_API_KEY` | `sk-proj-...` | OpenAI API key. Required for market analysis. |

### Wallet (live trading only)

| Variable | Example | Description |
|---|---|---|
| `PRIVATE_KEY` | `0xabc123...` | Polygon wallet private key (with `0x` prefix). Only needed for live trading. |

### Trading Mode

| Variable | Default | Description |
|---|---|---|
| `PAPER_TRADING` | `true` | Set to `false` for live trading. **Never change without explicit intent.** |

### Risk Parameters

| Variable | Default | Description |
|---|---|---|
| `MAX_POSITION_SIZE_USDC` | `50` | Maximum size of a single position in USDC. |
| `MAX_TOTAL_EXPOSURE_USDC` | `200` | Maximum total portfolio exposure in USDC. |
| `MIN_EDGE_THRESHOLD` | `0.10` | Minimum edge (10%) required to generate a trade signal. |
| `KELLY_FRACTION` | `0.25` | Fraction of Kelly criterion to use. 0.25 = quarter Kelly (conservative). |

### Market Discovery Filters

| Variable | Default | Description |
|---|---|---|
| `MIN_VOLUME_24H` | `1000` | Minimum 24-hour trading volume (USDC) to consider a market. |
| `MIN_LIQUIDITY` | `500` | Minimum liquidity (USDC) to consider a market. |
| `MAX_MARKETS_PER_CYCLE` | `10` | Maximum number of markets to analyze per cycle. |

### Timing

| Variable | Default | Description |
|---|---|---|
| `LOOP_INTERVAL` | `300` | Seconds between trading cycles (5 minutes). |
| `ORDER_CHECK_INTERVAL` | `60` | Seconds between order status checks. |

### Analysis

| Variable | Default | Description |
|---|---|---|
| `OPENAI_MODEL` | `gpt-4o` | OpenAI model used for market analysis. |
| `ENABLE_WEB_SEARCH` | `true` | Enable web search tool in OpenAI analysis. |

### Infrastructure

| Variable | Default | Description |
|---|---|---|
| `POLYMARKET_HOST` | `https://clob.polymarket.com` | Polymarket CLOB API endpoint. |
| `CHAIN_ID` | `137` | Polygon mainnet chain ID. |
| `DB_PATH` | `trading.db` | SQLite database file path. |
| `LOG_LEVEL` | `INFO` | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `LOG_FILE` | `trading.log` | Log file path. |

## Example `.env`

### Minimal (paper trading)
```env
OPENAI_API_KEY=sk-proj-your-key-here
```

### Full (live trading)
```env
PRIVATE_KEY=0xYourPrivateKeyHere
OPENAI_API_KEY=sk-proj-your-key-here
PAPER_TRADING=false
MAX_POSITION_SIZE_USDC=100
MAX_TOTAL_EXPOSURE_USDC=500
MIN_EDGE_THRESHOLD=0.08
KELLY_FRACTION=0.20
LOOP_INTERVAL=600
```

## Tuning Guide

### More conservative
- Increase `MIN_EDGE_THRESHOLD` (e.g., `0.15`) — only trade when very confident
- Decrease `KELLY_FRACTION` (e.g., `0.10`) — smaller positions
- Decrease `MAX_POSITION_SIZE_USDC` and `MAX_TOTAL_EXPOSURE_USDC`

### More aggressive
- Decrease `MIN_EDGE_THRESHOLD` (e.g., `0.05`) — trade more often
- Increase `KELLY_FRACTION` (e.g., `0.50`) — larger positions (higher risk)
- Increase exposure limits

### Faster cycles
- Decrease `LOOP_INTERVAL` (e.g., `120`) — more frequent analysis
- Increase `MAX_MARKETS_PER_CYCLE` — analyze more markets per cycle
- Note: faster cycles consume more OpenAI API credits
