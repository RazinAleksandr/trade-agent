# Phase 1: Instrument Layer - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Stateless Python CLI tools that fetch markets, retrieve prices, calculate edge, size positions, execute trades (paper + live), track portfolio, and persist data. Each tool lives in `tools/` and is invoked independently via `python tools/<name>.py`. Shared logic lives in `lib/`. The agent layer (Phase 2) calls these tools via Bash — no decision-making happens in this layer.

</domain>

<decisions>
## Implementation Decisions

### CLI Tool Interface
- **D-01:** Tools use `argparse` for argument parsing. Auto-generated `--help`. Agent passes flags like `--min-volume 1000 --format json`.
- **D-02:** All tools output JSON to stdout. Human-readable mode via `--pretty` flag. No table format — JSON only.
- **D-03:** Errors reported as JSON to stderr (`{"error": "message", "code": "INVALID_ARG"}`) with non-zero exit codes. Different exit codes for different error types.
- **D-04:** Each tool is a single-purpose script — one script per action (e.g., `discover_markets.py`, `get_prices.py`, `execute_trade.py`, `get_portfolio.py`). No subcommands.

### Shared Infrastructure
- **D-05:** Shared code lives in `lib/` package (config, db, models, logging). `tools/` has CLI entry points that import from `lib/`. Clean separation of CLI from reusable logic.
- **D-06:** Old v1 root `.py` files (main.py, market_discovery.py, trader.py, etc.) are deleted after cherry-picking useful logic into `tools/` + `lib/`. No legacy files left in root.
- **D-07:** Config continues to load from `.env` via `python-dotenv`. Each tool imports from `lib/config.py`. Same proven pattern as v1.
- **D-08:** Tools accept CLI flag overrides for config values (e.g., `--min-volume 5000` overrides `MIN_VOLUME_24H` from `.env`). Env vars are defaults, flags override.

### Paper Trade Pricing
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

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Success Criteria
- `.planning/REQUIREMENTS.md` — INST-01 through INST-13 (all Phase 1 requirements), SAFE-01, SAFE-02, SAFE-05
- `.planning/ROADMAP.md` — Phase 1 success criteria (5 acceptance tests)

### API Integration
- `docs/api-reference.md` — Gamma API endpoints, CLOB API order flow, authentication details
- `docs/wallet-setup.md` — Wallet generation, L2 credential derivation, token allowances for live mode
- `.planning/codebase/INTEGRATIONS.md` — Full external API inventory with hosts, auth, and contract addresses

### Existing Code (reference for cherry-picking)
- `market_discovery.py` — Gamma API integration, Market dataclass, stringified JSON parsing
- `trader.py` — py-clob-client order execution, paper/live mode switching, OrderResult dataclass
- `data_store.py` — SQLite schema (5 tables), CRUD operations
- `strategy.py` — Kelly criterion math, TradeSignal dataclass
- `portfolio.py` — Position tracking, resolved market detection, risk limit checks
- `config.py` — .env loading pattern, all parameter definitions
- `logger_setup.py` — Dual logging setup (console + JSON file)

### Architecture & Conventions
- `.planning/codebase/CONVENTIONS.md` — Naming patterns, code style, error handling patterns
- `docs/trading-engine.md` — Kelly criterion derivation, edge calculation formulas
- `docs/configuration.md` — All env vars with defaults and tuning guide

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `market_discovery.py`: `Market` dataclass (11 fields), `fetch_active_markets()` with Gamma API parsing, `_parse_market()` with stringified JSON handling — core logic directly reusable in `tools/discover_markets.py`
- `trader.py`: `Trader` class with paper/live mode switching, py-clob-client wrapper, `OrderResult` dataclass — order signing and posting logic reusable
- `data_store.py`: Full SQLite schema (trades, positions, decisions, market_snapshots, strategy_metrics), CRUD methods — schema and query logic reusable in `lib/db.py`
- `strategy.py`: `kelly_criterion()` function, `TradeSignal` dataclass — pure math, directly reusable
- `portfolio.py`: `PortfolioManager` with P&L calculation, risk limit checks, resolved market detection — tracking logic reusable
- `config.py`: .env loading pattern with `python-dotenv` — pattern reusable in `lib/config.py`
- `logger_setup.py`: `get_logger()` factory, `JsonFormatter` — reusable in `lib/logging.py`

### Established Patterns
- Dataclasses for data models: `Market`, `MarketAnalysis`, `TradeSignal`, `OrderResult`
- Try/except with safe defaults: empty list on discovery failure, None on analysis failure
- Lazy singletons for expensive resources (e.g., OpenAI client)
- Constants from config module, not hardcoded

### Integration Points
- Gamma API: `https://gamma-api.polymarket.com` — public, no auth
- CLOB API: `https://clob.polymarket.com` — read endpoints public, write needs L2 auth
- SQLite: `trading.db` — local file, auto-created
- Polygon RPC: `https://polygon-rpc.com` — only for live mode wallet setup

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-instrument-layer*
*Context gathered: 2026-03-26*
