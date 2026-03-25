# Architecture

**Analysis Date:** 2025-03-25

## Pattern Overview

**Overall:** Event-driven pipeline architecture with separation of concerns across functional layers.

**Key Characteristics:**
- Sequential trading cycle orchestrated by central event loop
- Stateless analysis layer independent of execution
- Pluggable paper/live trading mode switching
- Persistent decision tracking via SQLite
- Parallel market analysis with thread pool for throughput

## Layers

**Configuration & Setup:**
- Purpose: Centralized parameter management, wallet initialization for live mode
- Location: `config.py`, `setup_wallet.py`
- Contains: Environment variable loading, Ethereum account generation, token allowances
- Depends on: `python-dotenv`, `eth-account`, `web3.py` (live mode only)
- Used by: All other modules load from `config.py`

**Data Persistence:**
- Purpose: Record all trades, positions, decisions, and strategy metrics for audit and analysis
- Location: `data_store.py`
- Contains: SQLite schema with 5 tables (trades, positions, decisions, market_snapshots, strategy_metrics), CRUD operations
- Depends on: `sqlite3`, `config.py`
- Used by: `trader.py`, `portfolio.py`, `strategy.py`, `main.py`
- Key methods: `record_trade()`, `upsert_position()`, `get_open_positions()`, `get_strategy_stats()`

**Market Discovery:**
- Purpose: Fetch and filter tradable markets from Gamma API
- Location: `market_discovery.py`
- Contains: `Market` dataclass, Gamma API client, JSON parsing for stringified API fields, filter logic
- Depends on: `requests`, `config.py`, `logger_setup.py`
- Used by: `main.py` (market fetching), `trader.py` (market refresh), `portfolio.py` (price/resolution updates)
- Key functions: `fetch_active_markets()` (discovery), `fetch_market_by_id()` (single lookup)

**Analysis Engine:**
- Purpose: Generate probability estimates using OpenAI GPT-4o with web search for informed decisions
- Location: `market_analyzer.py`
- Contains: `MarketAnalysis` dataclass, OpenAI client (lazy singleton), prompt template, JSON response parsing, parallel analysis coordinator
- Depends on: `openai`, `config.py`, `logger_setup.py`, `concurrent.futures`
- Used by: `main.py` (analysis step)
- Key functions: `analyze_market()` (single), `batch_analyze()` (parallel with ThreadPoolExecutor, max_workers=4)
- Key abstractions: OpenAI Responses API with optional `web_search` tool based on `ENABLE_WEB_SEARCH` config

**Strategy & Signal Generation:**
- Purpose: Convert market analyses into trade signals with Kelly criterion sizing and edge filtering
- Location: `strategy.py`
- Contains: `TradeSignal` dataclass, Kelly criterion formula, signal evaluation logic, position conflicts check
- Depends on: `market_analyzer.MarketAnalysis`, `data_store.DataStore`, `config.py`, `logger_setup.py`
- Used by: `main.py` (signal generation)
- Key functions: `generate_signals()` (batch with capital allocation), `kelly_criterion()` (position sizing math), `_evaluate_signal()` (individual analysis → signal)
- Decision gates: minimum edge threshold (`MIN_EDGE_THRESHOLD`), confidence-adjusted edge, Kelly sizing > 0, position size >= $1 min

**Trading Execution:**
- Purpose: Execute trade signals via py-clob-client (live) or record locally (paper)
- Location: `trader.py`
- Contains: `Trader` class (paper/live mode switch), `OrderResult` dataclass, py-clob-client wrapper, order signing/posting
- Depends on: `py_clob_client`, `config.py`, `data_store.DataStore`, `logger_setup.py`
- Used by: `main.py` (signal execution)
- Key methods: `execute_signal()` (router), `_paper_trade()` (record only), `_live_trade()` (sign + post to CLOB)
- Trading details: GTC (Good-Til-Cancel) limit orders, signature_type=0 for EOA wallets, token ID derived from signal side

**Portfolio Management:**
- Purpose: Track positions, monitor P&L, detect resolved markets, enforce risk limits
- Location: `portfolio.py`
- Contains: `PortfolioManager` class with position tracking, risk checks, portfolio summary
- Depends on: `data_store.DataStore`, `market_discovery.fetch_market_by_id()`, `config.py`, `logger_setup.py`
- Used by: `main.py` (post-execution monitoring)
- Key methods: `update_position_prices()` (mark-to-market), `check_for_resolved_markets()` (auto-close), `check_risk_limits()` (exposure warnings), `print_portfolio()` (console output)

**Logging & Observability:**
- Purpose: Dual-format logging (human-readable console + JSON file) with structured decision tracking
- Location: `logger_setup.py`
- Contains: `get_logger()` (per-module loggers), `JsonFormatter` (JSON serialization), `log_decision()` (structured decision logging)
- Depends on: `logging`, `json`, `config.py`
- Used by: All modules
- Output: Console to stdout, JSON to file specified in `LOG_FILE` config

**Orchestration & Main Loop:**
- Purpose: Coordinate full trading cycle, manage lifecycle, handle graceful shutdown
- Location: `main.py`
- Contains: `run_trading_cycle()` (6-step pipeline), `run_strategy_update()` (periodic review), `signal_handler()` (SIGINT/SIGTERM)
- Depends on: All other modules
- Key lifecycle: Initialize (config validation, component setup) → loop until shutdown → graceful close (cleanup, final summary)

## Data Flow

**Single Trading Cycle (6 Steps):**

1. **Market Discovery** → Gamma API → `fetch_active_markets()` → returns `Market[]` filtered by volume/liquidity/price
2. **Market Snapshots** → `DataStore.record_market_snapshot()` → SQLite snapshots table (audit trail)
3. **Analysis** → `batch_analyze()` → ThreadPoolExecutor(4) → GPT-4o + web search → `MarketAnalysis[]`
4. **Signal Generation** → `generate_signals()` → Kelly sizing → `TradeSignal[]` (with capital allocation)
5. **Trade Execution** → `trader.execute_signal()` → paper (record) or live (CLOB API post) → `OrderResult`
6. **Portfolio Update** → `portfolio.update_position_prices()`, `check_for_resolved_markets()`, `check_risk_limits()`

**State Management:**
- Open positions tracked in `positions` table (market_id → side, price, size, P&L)
- Trades history in `trades` table (audit log of all executions)
- Decisions recorded in `decisions` table (analysis → signal → action chain)
- Current exposure calculated as SUM(cost_basis) from open positions
- Signal generation respects capital constraints: skip if max exposure reached, avoid duplicate market positions, size new positions within remaining capital

## Key Abstractions

**Market:**
- Purpose: Represents a single prediction market with pricing and metadata
- Examples: `market_discovery.Market` dataclass with 11 fields (id, question, tokens, prices, volume, liquidity, dates)
- Pattern: Immutable data container; created by API parsing in `_parse_market()`, passed through analysis → strategy → execution pipeline

**MarketAnalysis:**
- Purpose: Output of GPT-4o analysis with probability estimate and confidence
- Examples: `market_analyzer.MarketAnalysis` dataclass with 10 fields (market data + estimated_prob, confidence, edge, reasoning, sources)
- Pattern: Enriches market with analysis; edge = estimated_prob - market_price; used by strategy to generate signals

**TradeSignal:**
- Purpose: Intent to execute a trade with sizing and justification
- Examples: `strategy.TradeSignal` dataclass with 11 fields (market, side, price, size, cost, Kelly values, confidence, reasoning)
- Pattern: Product of signal generation; passed to trader for execution; contains all info needed to post order

**OrderResult:**
- Purpose: Outcome of trade execution (paper or live)
- Examples: `trader.OrderResult` dataclass with order_id, success flag, message, mode flag
- Pattern: Returned from `execute_signal()`; logged; determines if position recorded

## Entry Points

**Main Agent Loop:**
- Location: `main.py:main()`
- Triggers: `python main.py` command
- Responsibilities: Validate config, initialize components, run cycles until shutdown, cleanup
- Cycle interval: `LOOP_INTERVAL` config (default 300s)

**Wallet Setup:**
- Location: `setup_wallet.py` (script-style, not imported)
- Triggers: `python setup_wallet.py` (one-time before live trading)
- Responsibilities: Generate/import wallet, derive L2 API credentials, set token allowances on Polygon

**Tests:**
- Location: `tests/test_paper_trading.py`
- Triggers: `python tests/test_paper_trading.py`
- Responsibilities: Smoke tests of key modules (config, data_store, market_discovery, strategy, portfolio, trader)

## Error Handling

**Strategy:** Fail-safe defaults with logging and cycle continuation.

**Patterns:**
- Discovery failure: Log error, return empty markets list, skip cycle
- Analysis failure: Log error per market, return only successful analyses, signal generation proceeds with what's available
- Signal generation failure: Log error, return partial signals, trade execution proceeds with what's available
- Execution failure: Log error per signal, record as failed, portfolio update continues
- Portfolio update failure: Log error, cycle continues
- Each failure includes try-except with descriptive logging; no exceptions escape the main loop (except on startup validation)

## Cross-Cutting Concerns

**Logging:** Dual format via `logger_setup.get_logger()` — console humanreadable, file JSON. Each module calls `get_logger(__name__)` once. Structured decisions logged via `log_decision()` with metadata (market_id, prices, signals, etc.)

**Validation:** Configuration loaded and validated at startup in `main()` before component init. Missing OPENAI_API_KEY exits immediately. Missing PRIVATE_KEY exits immediately if not in paper mode.

**Authentication:** Paper mode uses no auth. Live mode derives L2 API credentials from PRIVATE_KEY via `client.create_or_derive_api_creds()` in `Trader._init_live_client()`. Credentials set on client before order posting.

**Capital Management:** Bankroll tracked via `DataStore.get_total_exposure()` (sum of open position costs). Strategy respects `MAX_TOTAL_EXPOSURE_USDC` hard limit and `MAX_POSITION_SIZE_USDC` per-position limit. New signals sized to fit remaining capital.

**Risk Limits:** Portfolio checks execution at 90% of limits emit warnings. No forced liquidation; stops accepting new trades at hard limits.

---

*Architecture analysis: 2025-03-25*
