# External Integrations

**Analysis Date:** 2026-03-25

## APIs & External Services

**Polymarket Platform:**
- **Gamma API** - Market discovery and metadata
  - Host: `https://gamma-api.polymarket.com`
  - Client: `requests` library
  - Endpoints: `/markets`, `/markets/{id}`, `/events`
  - Used in: `market_discovery.py`
  - Auth: None (public API)

- **CLOB API** - Order placement and position management
  - Host: `https://clob.polymarket.com` (configurable via `POLYMARKET_HOST` env var)
  - Client: `py-clob-client` (py-clob-client wrapper around HTTP)
  - Used in: `trader.py`, `setup_wallet.py`
  - Auth: L2 API credentials (api_key, api_secret, api_passphrase) derived from private key via `create_or_derive_api_creds()`
  - Auth type: EOA signature_type=0 (Ethereum standard wallet, not Magic/email or browser proxy)
  - Key operations:
    - `create_order(OrderArgs)` - Create signed order
    - `post_order(signed_order, OrderType.GTC)` - Submit GTC (Good-Till-Canceled) limit order
    - `get_orders()` - Fetch open orders
    - `cancel()` - Cancel order by ID
    - `get_positions()` - Fetch live positions
    - `get_midpoint(token_id)` - Fetch orderbook midpoint price

**AI & Analysis:**
- **OpenAI API** - Market probability estimation via GPT-4o
  - Host: `https://api.openai.com`
  - Client: `openai` Python SDK
  - Model: `gpt-4o` (configurable via `OPENAI_MODEL` env var)
  - Auth: `OPENAI_API_KEY` environment variable
  - Integration: Responses API (`client.responses.create()`)
  - Tools: `web_search` enabled (real-time search for market analysis context)
  - Used in: `market_analyzer.py`
  - Parallelization: ThreadPoolExecutor with 4 workers for batch analysis (`batch_analyze()`)

## Data Storage

**Databases:**
- **SQLite** - Local persistence
  - Location: `trading.db` (path configurable via `DB_PATH` env var)
  - Client: Python `sqlite3` standard library
  - Purpose: Trade history, positions, decisions, market snapshots, strategy metrics
  - Schema: 5 tables (trades, positions, decisions, market_snapshots, strategy_metrics)
  - Accessed by: `data_store.py`
  - No external server; embedded local file-based database

**File Storage:**
- None (not applicable)

**Caching:**
- None (not applicable)

## Authentication & Identity

**Auth Provider:**
- Custom EOA (Externally Owned Account) wallet-based authentication
  - Implementation: Ethereum private key signing
  - Wallet generation: `eth_account.Account.create()` (see `setup_wallet.py`)
  - Signature type: 0 (EOA), NOT type 1 (Magic/email) or 2 (browser proxy)
  - Chain: Polygon mainnet (chain ID 137)
  - Private key source: `PRIVATE_KEY` environment variable (required for live trading only; paper trading does not need it)

**API Key Management:**
- OpenAI API Key: `OPENAI_API_KEY` environment variable
- CLOB API Credentials: Derived on-the-fly from private key via `py_clob_client.create_or_derive_api_creds()`
  - Creds include: `api_key`, `api_secret`, `api_passphrase`
  - Valid for L2 authentication with CLOB API

## Monitoring & Observability

**Error Tracking:**
- None (not integrated)

**Logs:**
- Dual-channel logging via `logger_setup.py`:
  - **Console** (human-readable): stdout with format `%(asctime)s [%(levelname)s] %(name)s: %(message)s`
  - **File** (machine-readable JSON): `trading.log` (configurable via `LOG_FILE` env var)
  - Log level: configurable via `LOG_LEVEL` env var (default: INFO)
  - Structured decision logging: `log_decision()` function embeds JSON metadata for key events (trade signals, analysis, market snapshots)

## CI/CD & Deployment

**Hosting:**
- Not deployed; runs locally or on user's infrastructure
- Autonomous loop via `main.py`

**CI Pipeline:**
- None (not configured)

**Graceful Shutdown:**
- Signal handlers: SIGINT and SIGTERM
- Cleanup on exit: position summary, strategy metrics, database closure

## Environment Configuration

**Required env vars:**
- `OPENAI_API_KEY` - OpenAI API authentication (required for market analysis)
- `PRIVATE_KEY` - Ethereum private key for live trading (required only if `PAPER_TRADING=false`)

**Optional env vars:**
- `PAPER_TRADING` (default: true) - Enable/disable live trading mode
- `POLYMARKET_HOST` (default: https://clob.polymarket.com) - CLOB API host override
- `CHAIN_ID` (default: 137) - Polygon chain ID
- `MAX_POSITION_SIZE_USDC` (default: 50) - Max single position sizing
- `MAX_TOTAL_EXPOSURE_USDC` (default: 200) - Max portfolio exposure limit
- `MIN_EDGE_THRESHOLD` (default: 0.10) - Minimum 10% edge to trade
- `KELLY_FRACTION` (default: 0.25) - Quarter-Kelly position sizing fraction
- `MIN_VOLUME_24H` (default: 1000) - Market volume filter
- `MIN_LIQUIDITY` (default: 500) - Market liquidity filter
- `MAX_MARKETS_PER_CYCLE` (default: 10) - Markets to analyze per cycle
- `LOOP_INTERVAL` (default: 300) - Seconds between trading cycles
- `ORDER_CHECK_INTERVAL` (default: 60) - Seconds between order status checks
- `DB_PATH` (default: trading.db) - SQLite database file path
- `LOG_LEVEL` (default: INFO) - Python logging level
- `LOG_FILE` (default: trading.log) - Structured JSON log file path
- `OPENAI_MODEL` (default: gpt-4o) - OpenAI model override
- `ENABLE_WEB_SEARCH` (default: true) - OpenAI Responses API web search tool

**Secrets location:**
- `.env` file in project root (must never be committed)
- Never hardcoded in source files
- Loaded via `python-dotenv` in `config.py`

## Webhooks & Callbacks

**Incoming:**
- None (not applicable)

**Outgoing:**
- None (not applicable)

## On-Chain Integration (Polygon Mainnet)

**Smart Contracts:**
- **USDC Token** - Address: `0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174`
  - Function: `approve(spender, amount)` for Exchange allowance
  - Used in: `setup_wallet.py` token allowance setup

- **CTF (Conditional Token Framework)** - Address: `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045`
  - Function: `setApprovalForAll(operator, approved)` for batch token approval
  - Used in: `setup_wallet.py` token allowance setup

- **Exchange** - Address: `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8B8982E`
  - Purpose: Primary Polymarket exchange contract
  - Requires: USDC approve + CTF setApprovalForAll

- **Neg-Risk Exchange** - Address: `0xC5d563A36AE78145C45a50134d48A1215220f80a`
  - Purpose: Separate contract for negative-risk (AMM-resolved) markets
  - Requires: USDC approve + CTF setApprovalForAll

**RPC Provider:**
- **Polygon RPC** - `https://polygon-rpc.com`
  - Used in: `setup_wallet.py` for wallet operations (gas price queries, tx submission, nonce tracking)
  - Provider type: Web3.py HTTPProvider

---

*Integration audit: 2026-03-25*
