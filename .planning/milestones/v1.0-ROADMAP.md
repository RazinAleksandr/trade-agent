# Roadmap: Polymarket Autonomous Trading Agent v2

## Overview

Build a two-layer autonomous trading system from the ground up: first a hardened Python instrument layer of stateless CLI tools the agent can call via Bash, then a multi-agent Claude Code layer (Scanner, Analyst, Risk Manager, Planner, Reviewer sub-agents) that calls those tools, then the strategy evolution feedback loop that makes the system self-improving, and finally scheduling and safety hardening that makes it safe to run unattended. Each phase delivers something independently verifiable before the next begins.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [ ] **Phase 1: Instrument Layer** - Stateless Python CLI tools for market data, order execution, and portfolio tracking
- [ ] **Phase 2: Agent Layer** - Multi-agent orchestration with 5 specialized Claude Code sub-agents
- [ ] **Phase 3: Strategy Evolution** - Self-improving strategy document with per-cycle reports and git versioning
- [ ] **Phase 4: Scheduling and Safety Hardening** - Cron/APScheduler cycle triggering, live trading gate, credential refresh

## Phase Details

### Phase 1: Instrument Layer
**Goal**: Operators can call stateless Python CLI tools that fetch markets, price data, execute trades, and track positions — with all critical edge cases hardened before any agent touches them
**Depends on**: Nothing (first phase)
**Requirements**: INST-01, INST-02, INST-03, INST-04, INST-05, INST-06, INST-07, INST-08, INST-09, INST-10, INST-11, INST-12, INST-13
**Success Criteria** (what must be TRUE):
  1. Running `python tools/discover_markets.py` returns a JSON list of active Polymarket markets filtered by volume, liquidity, and price range
  2. Running `python tools/execute_trade.py` in paper mode records a simulated fill priced at ask (buy) or bid (sell) using live orderbook data — not mid-price
  3. Running `python tools/get_portfolio.py` returns current open positions with unrealized P&L calculated from live prices
  4. Running any tool with invalid arguments prints a usage error to stderr and exits with non-zero code; SIGINT during execution completes the current operation cleanly before exit
  5. All tool output and errors are written to both console (human-readable) and a structured JSON log file; all parameters (edge threshold, Kelly fraction, max position, max exposure) are read from `.env`
**Plans:** 6 plans

Plans:
- [x] 01-01-PLAN.md — Foundation: lib/ package (config, models, db, logging, signals, errors) + test infra
- [x] 01-02-PLAN.md — Market data and pricing: Gamma API client, CLOB API pricing, discover_markets + get_prices tools
- [x] 01-03-PLAN.md — Strategy math: Kelly criterion, edge calculation, calculate_edge + calculate_kelly tools
- [x] 01-04-PLAN.md — Trade execution: paper + live trading, execute_trade tool
- [x] 01-05-PLAN.md — Portfolio tracking: positions, P&L, resolved markets, get_portfolio + check_resolved tools
- [x] 01-06-PLAN.md — V1 cleanup: delete legacy files, .env.example, integration verification

### Phase 2: Agent Layer
**Goal**: A main Claude Code agent can run a complete trading cycle — dispatching Scanner, Analyst, Risk Manager, Planner, and Reviewer sub-agents — that discovers markets, estimates probabilities, sizes positions, executes paper trades, and writes a cycle report
**Depends on**: Phase 1
**Requirements**: AGNT-01, AGNT-02, AGNT-03, AGNT-04, AGNT-05, AGNT-06, AGNT-07, AGNT-08, AGNT-09, AGNT-10
**Success Criteria** (what must be TRUE):
  1. Running the main agent cycle produces a cycle report in `state/reports/` listing markets considered, trades taken (or skipped), probability estimates, and reasoning for each decision
  2. Each sub-agent (Scanner, Analyst, Risk Manager, Planner, Reviewer) returns a structured JSON object matching its defined output schema — not prose — which the main agent parses without error
  3. The Analyst sub-agent runs a Bull/Bear debate for each candidate market and includes both perspectives in its probability estimate output
  4. The Risk Manager sub-agent detects when two open positions resolve on correlated outcomes and reduces combined sizing below the single-position maximum
  5. No sub-agent exceeds its configured `max_turns` limit; the main agent logs total token cost at cycle end
**Plans**: TBD
**UI hint**: no

### Phase 3: Strategy Evolution
**Goal**: After each trading cycle, the main agent updates `state/strategy.md` based on Reviewer analysis, creating an auditable history of strategy changes that the agent reads at the start of every subsequent cycle
**Depends on**: Phase 2
**Requirements**: STRT-01, STRT-02, STRT-03, STRT-04, STRT-05, STRT-06, STRT-07
**Success Criteria** (what must be TRUE):
  1. `state/strategy.md` starts as a blank document and after the first cycle contains the agent's initial observations written by the main agent — no pre-seeded rules
  2. After each cycle, `state/strategy.md` is updated and a new dated git commit is created, so running `git log state/strategy.md` shows one commit per completed cycle
  3. The "Core Principles" section of `state/strategy.md` remains unchanged across cycles regardless of what the agent writes elsewhere in the document
  4. Per-cycle markdown reports in `state/reports/` include: markets considered, trades taken, probability estimates, edge calculations, cycle P&L, and the agent's stated learnings
  5. Running the main agent at cycle start reads the current `state/strategy.md` and the last 3 cycle reports, and the Planner sub-agent references specific strategy rules in its trade plan output
**Plans:** 2 plans

Plans:
- [x] 03-01-PLAN.md — Foundation: schema validation, state files (strategy.md + core-principles.md), Strategy Updater agent, tests
- [ ] 03-02-PLAN.md — Pipeline integration: extend trading-cycle.md with Step 7 (Strategy Update) and core-principles.md reading

### Phase 4: Scheduling and Safety Hardening
**Goal**: The system runs unattended on a configurable schedule, refreshes expired CLOB credentials automatically, and requires explicit multi-step confirmation before any live trade is placed
**Depends on**: Phase 3
**Requirements**: SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05, STRT-07
**Success Criteria** (what must be TRUE):
  1. A cron entry or APScheduler daemon triggers full trading cycles at a configurable interval; the cycle log shows the scheduled start time and completion time for each run
  2. When the CLOB API returns a 401 response during a cycle, the system re-derives L2 credentials and retries the request without failing the cycle
  3. Attempting to enable live trading with `PAPER_TRADING=false` in `.env` produces a confirmation prompt that displays current paper P&L, requires typing "CONFIRM LIVE" to proceed, and blocks live trading if paper P&L across the configured minimum cycle count is negative
  4. Paper mode order fills are priced at ask (buys) and bid (sells) from the live orderbook — not at mid-price — and order sizes are normalized to max 2 decimal places with minimum 5 USDC notional before any order is recorded or placed
**Plans:** 3 plans

Plans:
- [x] 04-01-PLAN.md — Safety core: Config extensions, 401 credential refresh, gate-pass check, DataStore cycle stats
- [x] 04-02-PLAN.md — Scheduling: cron wrapper script with PID lockfile, crontab setup tool
- [x] 04-03-PLAN.md — Live trading gate tool and safety verification tests (SAFE-01 through SAFE-05)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Instrument Layer | 0/6 | Planning complete | - |
| 2. Agent Layer | 0/TBD | Not started | - |
| 3. Strategy Evolution | 0/2 | Planning complete | - |
| 4. Scheduling and Safety Hardening | 0/3 | Planning complete | - |
