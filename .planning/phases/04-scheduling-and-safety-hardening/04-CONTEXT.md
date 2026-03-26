# Phase 4: Scheduling and Safety Hardening - Context

**Gathered:** 2026-03-27
**Status:** Ready for planning

<domain>
## Phase Boundary

The system runs unattended on a configurable schedule, refreshes expired CLOB credentials automatically, and requires explicit multi-step confirmation before any live trade is placed. SAFE-01 (paper default), SAFE-02 (realistic pricing), and SAFE-05 (order normalization) are already implemented in Phase 1 — this phase adds scheduling (STRT-07), live trading gate (SAFE-03), and credential refresh (SAFE-04).

</domain>

<decisions>
## Implementation Decisions

### Scheduling mechanism
- **D-01:** Cron + shell wrapper script. A crontab entry runs a wrapper script that invokes the `claude` CLI with the trading-cycle agent. No Python daemon — uses standard Unix scheduling.
- **D-02:** Lockfile guard to prevent overlapping cycles. Wrapper script checks for a lockfile before starting; if the previous cycle is still running, skip this invocation and log a warning. Use `flock` or PID-based lock.
- **D-03:** Fixed interval via `CYCLE_INTERVAL` env var in `.env` (e.g., `"4h"`, `"1d"`, `"30m"`). Wrapper script or setup tool translates to crontab syntax. Matches existing config pattern — all parameters in `.env`.
- **D-04:** Setup script `tools/setup_schedule.py` reads `CYCLE_INTERVAL` from `.env` and installs/updates the crontab entry. `--remove` flag to uninstall. Follows the existing `tools/` CLI pattern.

### Live trading gate
- **D-05:** Separate gate tool `tools/enable_live.py` — checks paper P&L, displays it, requires typing "CONFIRM LIVE", and writes a gate-pass file. Clean separation from trade execution logic.
- **D-06:** Configurable minimum paper cycles via `MIN_PAPER_CYCLES` env var (default 10). Gate tool queries SQLite for completed paper cycle count and aggregate P&L. Must have >= N cycles AND positive cumulative P&L to pass.
- **D-07:** One-time persistent gate file (`.live-gate-pass`). Written after successful confirmation. `execute_trade` checks for this file before placing live orders. Delete the file to re-lock. Re-run `enable_live.py` to re-verify conditions.
- **D-08:** Gate-pass check in `execute_trade.py` — if `PAPER_TRADING=false` and no `.live-gate-pass` file exists, refuse to execute live trades with clear error message.

### Credential refresh
- **D-09:** Claude's discretion on credential refresh implementation (SAFE-04). Hook retry logic into `lib/trading.py` for 401 responses — re-derive L2 credentials and retry the request. Also apply to `lib/pricing.py` for orderbook reads.

### Already-satisfied requirements
- **D-10:** SAFE-01 (paper default) — already implemented in `Config.paper_trading = True`. Verify with test coverage.
- **D-11:** SAFE-02 (realistic paper pricing) — already implemented via `get_fill_price()` in `lib/pricing.py` (best ask for buys, best bid for sells). Verify with test coverage.
- **D-12:** SAFE-05 (order normalization) — already implemented in `validate_order()` in `lib/trading.py` (2 decimal places, min 5 USDC). Verify with test coverage.

### Claude's Discretion
- Wrapper script implementation details (shell script structure, logging format)
- Lockfile implementation approach (flock vs PID file)
- `CYCLE_INTERVAL` parsing and crontab translation logic
- Credential refresh retry count and backoff strategy
- Gate-pass file format and location
- How `enable_live.py` calculates aggregate paper P&L from SQLite
- Test coverage approach for already-satisfied requirements

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Success Criteria
- `.planning/REQUIREMENTS.md` — SAFE-01 through SAFE-05 (safety requirements), STRT-07 (scheduling)
- `.planning/ROADMAP.md` — Phase 4 success criteria (4 acceptance tests)

### Phase 1 Decisions (instrument layer)
- `.planning/phases/01-instrument-layer/01-CONTEXT.md` — D-09 (paper pricing at ask/bid), D-10 (no fake fills), D-11 (paper needs CLOB read access), order validation

### Phase 2 Decisions (agent layer)
- `.planning/phases/02-agent-layer/02-CONTEXT.md` — D-02 (skip-and-continue on failures), D-03 (Claude Code as main agent, sub-agents via Task)

### Phase 3 Decisions (strategy evolution)
- `.planning/phases/03-strategy-evolution/03-CONTEXT.md` — D-10 (parameter adjustments are suggestions only)

### Existing Implementation
- `lib/trading.py` — Current paper and live trade execution (validate_order, execute_paper_trade, execute_live_trade)
- `lib/config.py` — Config dataclass with load_config() factory
- `lib/pricing.py` — get_fill_price() for CLOB orderbook pricing
- `lib/db.py` — DataStore with trades, positions tables (needed for P&L calculation)
- `.claude/agents/trading-cycle.md` — Full 8-step trading cycle agent
- `setup_wallet.py` — Wallet generation, L2 credential derivation, token allowances

### API Integration
- `.planning/codebase/INTEGRATIONS.md` — CLOB API auth details, L2 credential derivation via `create_or_derive_api_creds()`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/trading.py`: `validate_order()` already handles SAFE-05. `execute_live_trade()` creates fresh `ClobClient` per call and derives credentials — credential refresh can wrap this with retry logic.
- `lib/pricing.py`: `get_fill_price()` already handles SAFE-02 (best ask for buys, best bid for sells). May need 401 retry wrapper for credential expiry.
- `lib/config.py`: `Config` dataclass and `load_config()` factory — new env vars (`CYCLE_INTERVAL`, `MIN_PAPER_CYCLES`) follow existing pattern.
- `lib/db.py`: `DataStore` with `get_open_positions()`, trade recording — provides the paper P&L data needed by the live trading gate.
- `setup_wallet.py`: Existing wallet/credential setup script — reference for L2 credential derivation flow.

### Established Patterns
- Tools in `tools/` are single-purpose CLI scripts with argparse (Phase 1 D-01, D-04)
- Config from `.env` via `load_config()` — new params follow the same pattern
- `ClobClient` in `execute_live_trade()` already derives credentials each call via `create_or_derive_api_creds()`

### Integration Points
- `tools/setup_schedule.py` (new) — reads CYCLE_INTERVAL, manages crontab
- `tools/enable_live.py` (new) — live trading gate, writes gate-pass file
- `run_cycle.sh` (new) — wrapper script invoked by cron, handles lockfile, invokes `claude` CLI
- `lib/trading.py` — needs gate-pass check in live execution path, credential refresh on 401
- `lib/pricing.py` — may need credential refresh on 401 for authenticated endpoints

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

*Phase: 04-scheduling-and-safety-hardening*
*Context gathered: 2026-03-27*
