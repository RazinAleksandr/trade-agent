---
phase: 01-instrument-layer
plan: 02
subsystem: market-data
tags: [gamma-api, clob-api, pricing, market-discovery, requests, py-clob-client, argparse, cli]

# Dependency graph
requires:
  - "01-01: lib/ package with config, models, errors, logging_setup, signals"
provides:
  - "lib/market_data.py: Gamma API client with fetch_active_markets, fetch_market_by_id, neg-risk detection"
  - "lib/pricing.py: CLOB API pricing with inverted side semantics (get_fill_price, get_best_bid, get_best_ask)"
  - "tools/discover_markets.py: CLI tool for market discovery (INST-01)"
  - "tools/get_prices.py: CLI tool for orderbook prices (INST-02)"
affects: [01-03, 01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: [pytest-timeout]
  patterns: [gamma-api-stringified-json, clob-inverted-side-semantics, cli-sys-path-setup]

key-files:
  created:
    - lib/market_data.py
    - lib/pricing.py
    - tools/__init__.py
    - tools/discover_markets.py
    - tools/get_prices.py
    - tests/test_market_data.py
    - tests/test_pricing.py
    - tests/test_cli.py
  modified: []

key-decisions:
  - "get_fill_price inverts side semantics: BUY queries SELL book, SELL queries BUY book (verified from research)"
  - "Tools add project root to sys.path for lib/ importability when run as standalone scripts"
  - "Does NOT use get_order_book() anywhere -- only get_price() per Pitfall 3 (stale data)"
  - "All market_data functions take explicit params (no global config import)"

patterns-established:
  - "CLI tools: sys.path.insert(0, project_root) at top for lib/ access"
  - "Gamma API parsing: json.loads() for clobTokenIds and outcomePrices stringified fields"
  - "CLOB pricing: always use get_price() not get_order_book(), raise ValueError on zero price"
  - "Tools output JSON to stdout, errors to stderr via error_exit()"

requirements-completed: [INST-01, INST-02, INST-09]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 1 Plan 02: Market Data & Pricing Summary

**Gamma API market discovery with stringified JSON parsing and neg-risk detection, plus CLOB API pricing with correct inverted side semantics for paper trade fills, wrapped in two CLI tools**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T10:36:06Z
- **Completed:** 2026-03-26T10:41:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Gamma API client (lib/market_data.py) with fetch_active_markets, fetch_market_by_id, full stringified JSON handling, neg-risk detection, and configurable filters
- CLOB API pricing (lib/pricing.py) with correct inverted side semantics -- BUY fills at ask, SELL fills at bid -- and ValueError on no liquidity
- Two CLI tools (discover_markets.py, get_prices.py) with argparse, JSON stdout output, error_exit to stderr, --pretty flag, signal handling
- 34 passing tests across 3 test files (19 market_data + 10 pricing + 6 CLI tests, excluding 1 integration test)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/market_data.py and lib/pricing.py** - `034e494` (feat)
2. **Task 2: Create tools/discover_markets.py and tools/get_prices.py CLI wrappers** - `e5a89a7` (feat)

## Files Created/Modified
- `lib/market_data.py` - Gamma API client: fetch_active_markets, fetch_market_by_id, _parse_market (stringified JSON, neg-risk), _passes_filters
- `lib/pricing.py` - CLOB API pricing: get_fill_price (inverted semantics), get_best_bid, get_best_ask
- `tools/__init__.py` - Package marker for tools directory
- `tools/discover_markets.py` - CLI tool with --min-volume, --min-liquidity, --limit, --pretty
- `tools/get_prices.py` - CLI tool with --token-id (required), --pretty
- `tests/test_market_data.py` - 19 tests: parse_market, stringified JSON, neg-risk, filters, fetch (mocked)
- `tests/test_pricing.py` - 10 tests: fill price buy/sell, no liquidity, bid/ask, inverted semantics verification
- `tests/test_cli.py` - 6 tests: --help, invalid args, JSON output, missing required, signal handling

## Decisions Made
- get_fill_price inverts side semantics per CLOB API book-side convention: BUY calls get_price("SELL") for best ask, SELL calls get_price("BUY") for best bid
- Tools add project root to sys.path at module level for standalone execution (subprocess can't rely on PYTHONPATH)
- All lib/market_data.py functions take explicit parameters (gamma_api_url, min_volume, etc.) rather than importing config -- the CLI tools pass config values in
- Does NOT use get_order_book() anywhere per Pitfall 3 research (stale data issue GitHub #180)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added sys.path setup to CLI tools for lib/ importability**
- **Found during:** Task 2 (CLI tool testing)
- **Issue:** Running `python tools/discover_markets.py` as subprocess couldn't find `lib` module since tools/ is a subdirectory
- **Fix:** Added `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` to both CLI tools
- **Files modified:** tools/discover_markets.py, tools/get_prices.py
- **Verification:** All --help commands and CLI tests pass
- **Committed in:** e5a89a7 (Task 2 commit)

**2. [Rule 3 - Blocking] Fixed test_discover_markets_json_output __file__ reference in -c mode**
- **Found during:** Task 2 (CLI test execution)
- **Issue:** Subprocess test using `python -c` mode tried to use `__file__` which is undefined in -c mode
- **Fix:** Used f-string with PROJECT_ROOT constant to inject absolute path directly
- **Files modified:** tests/test_cli.py
- **Verification:** All 6 CLI tests pass
- **Committed in:** e5a89a7 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking issues)
**Impact on plan:** Both auto-fixes were necessary for tools to work as standalone scripts. No scope creep.

## Issues Encountered
- pytest-timeout was not installed; installed it at start (minor setup, no impact)

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with real API calls (mocked in tests).

## Next Phase Readiness
- lib/market_data.py and lib/pricing.py provide data foundation for all downstream plans
- tools/discover_markets.py and tools/get_prices.py are agent-callable CLI tools
- Plans 01-03 through 01-06 can import from lib.market_data and lib.pricing
- No blockers for wave 2 parallel plans

## Self-Check: PASSED

All 8 created files verified present. Both task commits (034e494, e5a89a7) verified in git log.

---
*Phase: 01-instrument-layer*
*Completed: 2026-03-26*
