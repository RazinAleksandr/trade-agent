<!-- GSD:project-start source:PROJECT.md -->
## Project

**Polymarket Autonomous Trading Agent v2**

A two-layer autonomous trading system for Polymarket prediction markets. The **instrument layer** provides Python tools for market data, order execution, and portfolio tracking. The **agent layer** is a multi-agent Claude system (running via Claude Code CLI) that uses those tools to discover opportunities, make trading decisions, execute trades, and continuously evolve its own strategy based on results — like a human financial analyst learning from experience.

**Core Value:** The agent must autonomously trade, analyze its own performance, and improve its strategy over time — no human intervention required between scheduled cycles.

### Constraints

- **Tech stack**: Python 3.12 for instrument layer, Claude Code CLI for agent layer
- **Agent runtime**: Claude Code sessions spawning sub-agents via Task tool, calling Python via Bash
- **Trading API**: Polymarket CLOB via py-clob-client
- **Analysis**: Claude sub-agents (not OpenAI) for market analysis
- **Persistence**: SQLite for trade data, markdown files for strategy/reports
- **Safety**: Paper trading default. Never live without explicit user configuration.
- **Existing code**: Review and cherry-pick, but don't inherit the old architecture
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12.9 - All source code, trading logic, analysis, and data persistence
## Runtime
- Python 3.12.9
- Virtual environment: `.venv/` (committed: no)
- pip (standard Python package manager)
- Lockfile: `requirements.txt` (present, pinned versions listed below)
## Frameworks
- `py-clob-client` (>=0.17.0) - Polymarket CLOB API client; handles order placement, position management, market data; core integration for live trading
- `web3` (>=7.0.0) - Ethereum/Polygon wallet interaction, token approvals, RPC connectivity for L2 operations
- `anthropic` (>=0.49.0) - AI integration (mentioned in requirements, may be deprecated in favor of OpenAI)
- `openai` (via OpenAI SDK, configured in code) - GPT-4o API for market probability estimation via Responses API with web search tool
- `requests` (>=2.31.0) - Gamma API HTTP client for market discovery and metadata
- `python-dotenv` (>=1.0.0) - Environment variable loading from `.env` files
- `eth-account` (>=0.13.0) - Ethereum wallet generation, account management, transaction signing for Polygon mainnet
## Key Dependencies
- `py-clob-client` (>=0.17.0) - Core trading execution; derives L2 API credentials, creates signed orders, posts to CLOB API
- `openai` - Market analysis engine; uses GPT-4o Responses API with `web_search` tool for real-time data
- `web3` (>=7.0.0) - Token approvals and on-chain operations for live trading (USDC approve, CTF setApprovalForAll)
- `requests` (>=2.31.0) - Gamma API HTTP requests for market discovery and event fetching
- `eth-account` (>=0.13.0) - Wallet generation and signing for EOA transactions
- `python-dotenv` (>=1.0.0) - Configuration management via environment variables
## Configuration
- Configuration via `.env` file (must exist, must never be committed)
- All parameters loaded through `config.py` via `python-dotenv`
- Example `.env` contents (never commit secrets):
- No build step required; Python runs directly
- `setup_wallet.py` is initialization script for live trading only (one-time use)
## Platform Requirements
- Python 3.12.9
- Virtual environment (`.venv/`)
- macOS, Linux, or Windows
- Internet connectivity for:
- Python 3.12.9 runtime
- Polygon mainnet chain ID: 137
- OPENAI_API_KEY required for market analysis
- PRIVATE_KEY required for live trading (optional for paper trading)
- SQLite3 (embedded in Python stdlib)
- Network access to all external APIs (see INTEGRATIONS.md)
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- All lowercase with underscores: `market_discovery.py`, `data_store.py`, `logger_setup.py`
- Purpose-driven names: module file names match their primary class/function (e.g., `strategy.py` contains `kelly_criterion()` and `TradeSignal`)
- Test files follow pattern: `test_*.py` in `tests/` directory
- Snake case: `fetch_active_markets()`, `batch_analyze()`, `kelly_criterion()`
- Private functions prefixed with underscore: `_parse_market()`, `_passes_filters()`, `_evaluate_signal()`, `_extract_json_from_response()`
- Descriptive verb-noun pattern: `record_trade()`, `upsert_position()`, `check_risk_limits()`
- Snake case throughout: `cycle_start`, `remaining_capital`, `estimated_prob`, `kelly_adjusted`
- Boolean flags: `paper_mode`, `is_paper`, `shutdown_requested`
- Constants in UPPERCASE: `PRIVATE_KEY`, `OPENAI_API_KEY`, `MAX_POSITION_SIZE_USDC` (in `config.py`)
- Loop variables: `m` for market, `t` for trade, `pos` for position, `c` for closed position (single letter for short-lived iterations)
- Dataclasses for data models: `@dataclass` used in `TradeSignal`, `Market`, `MarketAnalysis`, `OrderResult`
- Type hints on function parameters and returns: `def kelly_criterion(prob: float, odds_price: float, fraction: float = config.KELLY_FRACTION) -> float`
- Optional types: `Optional[ClobClient]`, `MarketAnalysis | None` (Python 3.12+ union syntax)
- Return type alternatives: `list[Market]`, `dict[str, float]`
## Code Style
- No explicit formatter (Black/ruff) configured — follows PEP 8 manually
- Indentation: 4 spaces
- Line length: practical limit ~100 characters (observed in code)
- Imports grouped: stdlib → third-party → local (with blank lines between groups)
- Trailing commas in multi-line structures
- No linter config found (no `.pylintrc`, `.flake8`, etc.)
- Code assumes PEP 8 style is maintained by convention
- Type hints used throughout but not enforced by mypy or similar
## Error Handling
- `fetch_active_markets()` in `market_discovery.py`: returns empty list on error
- `analyze_market()` in `market_analyzer.py`: returns None on JSON decode or OpenAI error
- `batch_analyze()`: catches individual failures but continues processing
- `_init_live_client()` in `trader.py`: catches and logs, falls back to paper mode
## Logging
- Info level: progress and cycle info — `log.info(f"Step 1: Discovering markets...")`
- Warning level: non-blocking issues — `log.warning(f"Could not fetch market {signal.market_id}")`
- Error level: failures with fallback — `log.error(f"Market discovery failed: {e}")`
- Console: human-readable with timestamp, level, module name
- File (`trading.log`): JSON format for machine parsing
## Comments
- Non-obvious algorithm explanation: Kelly criterion math in `strategy.py`
- Data format details: "Handle stringified JSON from Gamma API" in `market_discovery.py`
- Workarounds and tricky logic: "minimum $1 trade" threshold
- Docstrings on functions/classes: triple-quoted, brief description first
- Example from `strategy.py`:
## Function Design
- Positional for required params: `def kelly_criterion(prob: float, odds_price: float, ...)`
- Keyword-only config defaults: functions use `config.KELLY_FRACTION`, `config.MAX_POSITION_SIZE_USDC`
- Dataclass parameters preferred over many positional args
- Single return type per function
- Dataclasses for multi-field returns: `TradeSignal`, `OrderResult`, `MarketAnalysis`
- None for side-effect-only functions: `update_position_prices()`, `record_trade()`
- Safe defaults on error: `[]`, `None`, `{}`, `False`
## Module Design
- No subpackages; all `.py` files in project root per design
- Each module focused: `market_discovery.py` for Gamma API, `trader.py` for execution, `data_store.py` for persistence
## Architecture Patterns
- `Market`, `TradeSignal`, `MarketAnalysis`, `OrderResult` are dataclasses
- Cleaner than `{"market_id": "...", "price": 0.5}`
- `market_discovery.py`: API calls only
- `market_analyzer.py`: LLM analysis only
- `strategy.py`: signal generation (pure logic)
- `trader.py`: execution
- `portfolio.py`: position tracking and risk
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Sequential trading cycle orchestrated by central event loop
- Stateless analysis layer independent of execution
- Pluggable paper/live trading mode switching
- Persistent decision tracking via SQLite
- Parallel market analysis with thread pool for throughput
## Layers
- Purpose: Centralized parameter management, wallet initialization for live mode
- Location: `config.py`, `setup_wallet.py`
- Contains: Environment variable loading, Ethereum account generation, token allowances
- Depends on: `python-dotenv`, `eth-account`, `web3.py` (live mode only)
- Used by: All other modules load from `config.py`
- Purpose: Record all trades, positions, decisions, and strategy metrics for audit and analysis
- Location: `data_store.py`
- Contains: SQLite schema with 5 tables (trades, positions, decisions, market_snapshots, strategy_metrics), CRUD operations
- Depends on: `sqlite3`, `config.py`
- Used by: `trader.py`, `portfolio.py`, `strategy.py`, `main.py`
- Key methods: `record_trade()`, `upsert_position()`, `get_open_positions()`, `get_strategy_stats()`
- Purpose: Fetch and filter tradable markets from Gamma API
- Location: `market_discovery.py`
- Contains: `Market` dataclass, Gamma API client, JSON parsing for stringified API fields, filter logic
- Depends on: `requests`, `config.py`, `logger_setup.py`
- Used by: `main.py` (market fetching), `trader.py` (market refresh), `portfolio.py` (price/resolution updates)
- Key functions: `fetch_active_markets()` (discovery), `fetch_market_by_id()` (single lookup)
- Purpose: Generate probability estimates using OpenAI GPT-4o with web search for informed decisions
- Location: `market_analyzer.py`
- Contains: `MarketAnalysis` dataclass, OpenAI client (lazy singleton), prompt template, JSON response parsing, parallel analysis coordinator
- Depends on: `openai`, `config.py`, `logger_setup.py`, `concurrent.futures`
- Used by: `main.py` (analysis step)
- Key functions: `analyze_market()` (single), `batch_analyze()` (parallel with ThreadPoolExecutor, max_workers=4)
- Key abstractions: OpenAI Responses API with optional `web_search` tool based on `ENABLE_WEB_SEARCH` config
- Purpose: Convert market analyses into trade signals with Kelly criterion sizing and edge filtering
- Location: `strategy.py`
- Contains: `TradeSignal` dataclass, Kelly criterion formula, signal evaluation logic, position conflicts check
- Depends on: `market_analyzer.MarketAnalysis`, `data_store.DataStore`, `config.py`, `logger_setup.py`
- Used by: `main.py` (signal generation)
- Key functions: `generate_signals()` (batch with capital allocation), `kelly_criterion()` (position sizing math), `_evaluate_signal()` (individual analysis → signal)
- Decision gates: minimum edge threshold (`MIN_EDGE_THRESHOLD`), confidence-adjusted edge, Kelly sizing > 0, position size >= $1 min
- Purpose: Execute trade signals via py-clob-client (live) or record locally (paper)
- Location: `trader.py`
- Contains: `Trader` class (paper/live mode switch), `OrderResult` dataclass, py-clob-client wrapper, order signing/posting
- Depends on: `py_clob_client`, `config.py`, `data_store.DataStore`, `logger_setup.py`
- Used by: `main.py` (signal execution)
- Key methods: `execute_signal()` (router), `_paper_trade()` (record only), `_live_trade()` (sign + post to CLOB)
- Trading details: GTC (Good-Til-Cancel) limit orders, signature_type=0 for EOA wallets, token ID derived from signal side
- Purpose: Track positions, monitor P&L, detect resolved markets, enforce risk limits
- Location: `portfolio.py`
- Contains: `PortfolioManager` class with position tracking, risk checks, portfolio summary
- Depends on: `data_store.DataStore`, `market_discovery.fetch_market_by_id()`, `config.py`, `logger_setup.py`
- Used by: `main.py` (post-execution monitoring)
- Key methods: `update_position_prices()` (mark-to-market), `check_for_resolved_markets()` (auto-close), `check_risk_limits()` (exposure warnings), `print_portfolio()` (console output)
- Purpose: Dual-format logging (human-readable console + JSON file) with structured decision tracking
- Location: `logger_setup.py`
- Contains: `get_logger()` (per-module loggers), `JsonFormatter` (JSON serialization), `log_decision()` (structured decision logging)
- Depends on: `logging`, `json`, `config.py`
- Used by: All modules
- Output: Console to stdout, JSON to file specified in `LOG_FILE` config
- Purpose: Coordinate full trading cycle, manage lifecycle, handle graceful shutdown
- Location: `main.py`
- Contains: `run_trading_cycle()` (6-step pipeline), `run_strategy_update()` (periodic review), `signal_handler()` (SIGINT/SIGTERM)
- Depends on: All other modules
- Key lifecycle: Initialize (config validation, component setup) → loop until shutdown → graceful close (cleanup, final summary)
## Data Flow
- Open positions tracked in `positions` table (market_id → side, price, size, P&L)
- Trades history in `trades` table (audit log of all executions)
- Decisions recorded in `decisions` table (analysis → signal → action chain)
- Current exposure calculated as SUM(cost_basis) from open positions
- Signal generation respects capital constraints: skip if max exposure reached, avoid duplicate market positions, size new positions within remaining capital
## Key Abstractions
- Purpose: Represents a single prediction market with pricing and metadata
- Examples: `market_discovery.Market` dataclass with 11 fields (id, question, tokens, prices, volume, liquidity, dates)
- Pattern: Immutable data container; created by API parsing in `_parse_market()`, passed through analysis → strategy → execution pipeline
- Purpose: Output of GPT-4o analysis with probability estimate and confidence
- Examples: `market_analyzer.MarketAnalysis` dataclass with 10 fields (market data + estimated_prob, confidence, edge, reasoning, sources)
- Pattern: Enriches market with analysis; edge = estimated_prob - market_price; used by strategy to generate signals
- Purpose: Intent to execute a trade with sizing and justification
- Examples: `strategy.TradeSignal` dataclass with 11 fields (market, side, price, size, cost, Kelly values, confidence, reasoning)
- Pattern: Product of signal generation; passed to trader for execution; contains all info needed to post order
- Purpose: Outcome of trade execution (paper or live)
- Examples: `trader.OrderResult` dataclass with order_id, success flag, message, mode flag
- Pattern: Returned from `execute_signal()`; logged; determines if position recorded
## Entry Points
- Location: `main.py:main()`
- Triggers: `python main.py` command
- Responsibilities: Validate config, initialize components, run cycles until shutdown, cleanup
- Cycle interval: `LOOP_INTERVAL` config (default 300s)
- Location: `setup_wallet.py` (script-style, not imported)
- Triggers: `python setup_wallet.py` (one-time before live trading)
- Responsibilities: Generate/import wallet, derive L2 API credentials, set token allowances on Polygon
- Location: `tests/test_paper_trading.py`
- Triggers: `python tests/test_paper_trading.py`
- Responsibilities: Smoke tests of key modules (config, data_store, market_discovery, strategy, portfolio, trader)
## Error Handling
- Discovery failure: Log error, return empty markets list, skip cycle
- Analysis failure: Log error per market, return only successful analyses, signal generation proceeds with what's available
- Signal generation failure: Log error, return partial signals, trade execution proceeds with what's available
- Execution failure: Log error per signal, record as failed, portfolio update continues
- Portfolio update failure: Log error, cycle continues
- Each failure includes try-except with descriptive logging; no exceptions escape the main loop (except on startup validation)
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->

<!-- GSD:workflow-start source:GSD defaults -->
## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd:quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd:debug` for investigation and bug fixing
- `/gsd:execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->



<!-- GSD:profile-start -->
## Developer Profile

> Profile not yet configured. Run `/gsd:profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
