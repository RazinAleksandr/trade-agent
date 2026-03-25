# Codebase Concerns

**Analysis Date:** 2026-03-25

## Tech Debt

**Division by Zero in Strategy Sizing:**
- Issue: `strategy.py` line 140 divides position_size by price without guard against zero or invalid prices
- Files: `strategy.py:140`
- Impact: If price is calculated as 0 or invalid from market data, trading will crash
- Fix approach: Add explicit check `if price <= 0: return None` before division in `_evaluate_signal()`. Already has `0 < m.yes_price < 1` filter in discovery, but should double-check at execution point

**Price Edge Cases in Market Parser:**
- Issue: `market_discovery.py:121-122` defaults to 0.5 for missing prices but doesn't validate stringified JSON parsing
- Files: `market_discovery.py:121-122`
- Impact: If `json.loads()` on `outcomePrices` fails silently or returns None, defaults to 0.5 which may be incorrect
- Fix approach: Add explicit validation after json.loads() to ensure both prices are valid floats in range [0, 1]

**Database Connection Not Thread-Safe:**
- Issue: `data_store.py:14` opens single SQLite connection that may be shared across parallel threads in `market_analyzer.batch_analyze()`
- Files: `data_store.py:14`, `market_analyzer.py:182`
- Impact: SQLite in-memory transactions can deadlock or corrupt data if accessed concurrently
- Fix approach: Either wrap DataStore access in locks or configure SQLite with `timeout=10` parameter and enable WAL mode

**No Rate Limiting for OpenAI API:**
- Issue: `market_analyzer.batch_analyze()` spawns 4 parallel workers without rate limiting or retry backoff
- Files: `market_analyzer.py:182-192`
- Impact: May hit OpenAI rate limits and silently drop analyses (failed futures just log, don't retry)
- Fix approach: Add exponential backoff with max 3 retries on API errors, or implement request queue with delays

**Hardcoded Position Size Limits:**
- Issue: `strategy.py:130-134` applies position sizing limits but doesn't account for existing open positions in same market
- Files: `strategy.py:130-134`
- Impact: Could exceed per-market exposure if agent re-analyzes same market in subsequent cycles
- Fix approach: Track per-market exposure in addition to total exposure check already in `strategy.py:56-61`

## Known Bugs

**Incorrect Kelly Fraction Application:**
- Symptoms: `strategy.py:147` rounds price to 2 decimals but Kelly calculation uses full precision — inconsistency between sizing math and execution
- Files: `strategy.py:123-147`
- Trigger: Any market where full-precision price differs from 2-decimal rounded price
- Workaround: Use rounded price in Kelly calculation too: `kelly_raw = kelly_criterion(prob, round(price, 2), ...)`

**Market Resolution Detection Gap:**
- Symptoms: `portfolio.py:50-69` checks `market.closed` but Gamma API may return stale data; positions not closed until next cycle
- Files: `portfolio.py:50-69`
- Trigger: Market resolves during cycle but agent doesn't know until next refresh
- Workaround: Add periodic market status refresh separate from price updates, or rely on CLOB API for order fills

**Win Rate Calculation with No Closed Positions:**
- Symptoms: `data_store.py:215` falls back to edge-based win rate when no positions closed yet, but edge estimates are not realized outcomes
- Files: `data_store.py:208-220`
- Trigger: Early-stage agent with paper trades but no resolved markets
- Workaround: Clearly document that early win_rate is estimated, not realized; add metadata flag `calculated_from_edge: bool`

## Security Considerations

**Private Key Exposure in Debug Output:**
- Risk: `setup_wallet.py:32` prints private key and credentials to stdout
- Files: `setup_wallet.py:32`, `setup_wallet.py:51-53`
- Current mitigation: Instructions say "save securely" but no actual protection
- Recommendations: Use `getpass()` for interactive input, never print full keys, only show checksum or last 4 chars

**API Credentials in Logs:**
- Risk: `logger_setup.py:10-20` may capture sensitive data in JSON logs if it's passed in log messages
- Files: `logger_setup.py:10-20`, `market_analyzer.py:160`
- Current mitigation: Log entries have `extra_data` dict but credentials should never be added
- Recommendations: Add log sanitization filter that redacts API keys, secrets, private keys; audit all `log_decision()` calls

**Web Search Enabled by Default:**
- Risk: `config.py:45` enables OpenAI web_search which may leak prompt content to external services
- Files: `config.py:45`, `market_analyzer.py:128`
- Current mitigation: Web search only used for market analysis (not secret data), but still external call
- Recommendations: Document privacy implications; consider opt-in instead of opt-out

**SQLite DB File Permissions:**
- Risk: `trading.db` contains trade history, positions, and strategy metrics — no encryption
- Files: `data_store.py:12-14`
- Current mitigation: .gitignore prevents commit, but file is world-readable on shared systems
- Recommendations: Set file permissions to 0600 after creation; consider encrypting SQLite with `sqlcipher`

## Performance Bottlenecks

**Sequential Market Fetching in Portfolio Update:**
- Problem: `portfolio.py:27-48` loops through positions and calls `fetch_market_by_id()` one-by-one
- Files: `portfolio.py:30-31`
- Cause: N+1 API calls if agent has many positions
- Improvement path: Batch fetch market data using Gamma API bulk endpoint or cache recent prices

**Parallel Analysis Without Timeout:**
- Problem: `market_analyzer.batch_analyze()` spawns 4 workers but workers have no timeout — one slow analysis blocks entire cycle
- Files: `market_analyzer.py:182-192`
- Cause: Future.result() called without timeout parameter
- Improvement path: Add timeout to `as_completed(futures, timeout=30)` to skip markets that take too long

**Repeated Gamma API Calls:**
- Problem: `main.py:104-108` fetches fresh market data again for execution after already analyzing same market
- Files: `main.py:104-108`
- Cause: Want fresh price at execution time, but doubles API load
- Improvement path: Cache market data for short window (5-10s), use cached version if available

**Sleep Loop in Main Cycle:**
- Problem: `main.py:213-216` uses `time.sleep(1)` in a loop to check shutdown flag every 1 second
- Files: `main.py:213-216`
- Cause: Inefficient polling; burns CPU if LOOP_INTERVAL is large (default 300s)
- Improvement path: Use event.wait(timeout) with threading.Event for shutdown signal

## Fragile Areas

**JSON Parsing from Gamma API:**
- Files: `market_discovery.py:110-119`
- Why fragile: Gamma API returns stringified JSON in `clobTokenIds` and `outcomePrices` fields with inconsistent naming (camelCase vs snake_case) and sometimes missing values
- Safe modification: Always test with live API responses; add schema validation; log raw JSON on parse failures
- Test coverage: Only basic smoke test `test_market_discovery()` checks one response; need coverage for edge cases (empty prices, missing tokens, wrong data types)

**OpenAI Response Parsing:**
- Files: `market_analyzer.py:73-97`
- Why fragile: Uses regex to extract JSON from Claude responses that may return markdown, code blocks, or invalid JSON
- Safe modification: Tighten JSON extraction regex; add fallback to re-request with stricter instruction; test with multiple model responses
- Test coverage: No test for malformed OpenAI responses; only live tests would catch parsing failures

**Portfolio Risk Limits:**
- Files: `portfolio.py:71-100`
- Why fragile: Warnings generated but never acted on (no automatic position closing or halt signal)
- Safe modification: Add explicit threshold for `risk["utilization"]` where agent stops placing new trades; clear log message when threshold crossed
- Test coverage: `test_portfolio()` only checks output format, not actual threshold enforcement

**Market Resolution Detection:**
- Files: `portfolio.py:50-69`
- Why fragile: Relies on Gamma API `market.closed` field which may lag reality or return incorrect values
- Safe modification: Query CLOB API for order fills as additional signal; check time-based resolution (if end_date < now, assume resolved)
- Test coverage: No test with actually-resolved markets; cannot verify closed position logic

## Scaling Limits

**Single SQLite Database:**
- Current capacity: ~100K rows before performance degrades significantly (no indexing)
- Limit: Will become bottleneck at ~10+ trades per cycle over months of operation
- Scaling path: Add indexes on `market_id`, `timestamp`, `status`; eventually migrate to PostgreSQL if needing historical analytics

**Parallel Analysis Workers Fixed at 4:**
- Current capacity: ~10-20 markets per cycle at 30s timeout per analysis
- Limit: OpenAI rate limits (RPM/tokens per minute) will be hit with more workers
- Scaling path: Make max_workers configurable; implement token counting and adaptive worker scaling

**Memory Growth from DataStore:**
- Current capacity: All trades/positions loaded into python objects in loops
- Limit: 10K+ trades will cause memory pressure on 4GB RAM systems
- Scaling path: Use database queries with LIMIT/OFFSET for pagination; avoid loading entire history into memory

## Dependencies at Risk

**py-clob-client Library:**
- Risk: Community-maintained SDK with limited updates; may break with Polymarket contract upgrades
- Impact: Live trading will fail if library becomes incompatible with new CLOB API versions
- Migration plan: Monitor GitHub releases; have fallback to direct HTTP requests to CLOB API; document expected signature format

**OpenAI Responses API:**
- Risk: Responses API is experimental (as of March 2025); may be deprecated or pricing may change significantly
- Impact: Analysis engine will need refactoring if API is removed or becomes cost-prohibitive
- Migration plan: Keep fallback to regular Completions API; implement cost tracking per analysis

**ethaccounts Library (eth-account):**
- Risk: Used only in setup_wallet.py; if Web3 ecosystem shifts, account signing may break
- Impact: New wallet setup will fail, but existing wallets still work
- Migration plan: Keep setup_wallet.py as reference; traders can manually fund wallet and set PRIVATE_KEY

## Missing Critical Features

**No Slippage Protection:**
- Problem: Trader executes at signal.price as GTC limit order but no safeguard if price moves adverse before fill
- Blocks: Cannot guarantee execution price in volatile markets; may miss profitable trades due to tight limits

**No Position Management:**
- Problem: Agent opens positions but has no logic to close winners early or cut losses
- Blocks: Positions stay open until market resolves (days/weeks), missing opportunity to re-deploy capital

**No Market Selection Bias Tracking:**
- Problem: No analysis of which market categories agent does well/poorly in
- Blocks: Cannot specialize strategy by market type; improvements are purely random

**No A/B Testing Framework:**
- Problem: No way to test different Kelly fractions, min_edge_thresholds, analysis prompts in parallel without manual changes
- Blocks: Cannot optimize parameters scientifically; tuning is trial-and-error

## Test Coverage Gaps

**No Live API Integration Tests:**
- What's not tested: Real Gamma API responses with edge cases (no prices, weird token IDs, missing fields)
- Files: `market_discovery.py`, `market_analyzer.py`
- Risk: Parser failures only discovered in production after encountering edge case
- Priority: High — discovery and analysis are critical path

**No Error Injection Tests:**
- What's not tested: Network timeouts, API 502 errors, malformed JSON responses
- Files: All API-calling modules
- Risk: Agent crashes or hangs on transient errors instead of gracefully degrading
- Priority: Medium — need resilience testing before live trading

**No Concurrency Tests:**
- What's not tested: DataStore used concurrently by multiple threads in batch_analyze()
- Files: `data_store.py`, `market_analyzer.py`
- Risk: Race conditions, SQLite locking issues only appear under load
- Priority: High — concurrent design is risky without verification

**No Edge Case Tests for Kelly Criterion:**
- What's not tested: Prices at extremes (0.01, 0.99), very high/low probabilities, extreme Kelly values
- Files: `strategy.py:27-46`
- Risk: Edge cases in sizing math produce invalid position sizes
- Priority: Medium — math is core to profitability

**No Live Trading Tests:**
- What's not tested: Actual order placement, signature verification, position tracking with real CLOB API
- Files: `trader.py`, entire trading loop
- Risk: First live trade may fail due to undiscovered issues (signature format, token ID format, order structure)
- Priority: Critical — must test before ANY live trading

---

*Concerns audit: 2026-03-25*
