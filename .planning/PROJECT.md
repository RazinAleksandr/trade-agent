# Polymarket Autonomous Trading Agent v2

## What This Is

A two-layer autonomous trading system for Polymarket prediction markets. The **instrument layer** provides Python tools for market data, order execution, and portfolio tracking. The **agent layer** is a multi-agent Claude system (running via Claude Code CLI) that uses those tools to discover opportunities, make trading decisions, execute trades, and continuously evolve its own strategy based on results — like a human financial analyst learning from experience.

## Core Value

The agent must autonomously trade, analyze its own performance, and improve its strategy over time — no human intervention required between scheduled cycles.

## Requirements

### Validated

- [x] Instrument layer: Python tools for market discovery, price data, order execution, portfolio tracking — *Validated in Phase 01: instrument-layer*
- [x] Agent layer: Claude Code main agent orchestrating sub-agents via Task tool — *Validated in Phase 02: agent-layer*
- [x] Sub-agent: Market Scanner — finds and filters interesting markets from Gamma API — *Validated in Phase 02: agent-layer*
- [x] Sub-agent: Market Analyst — deep-dives specific markets for probability estimation — *Validated in Phase 02: agent-layer*
- [x] Sub-agent: Risk Manager — evaluates portfolio risk and position sizing — *Validated in Phase 02: agent-layer*
- [x] Sub-agent: Planner — reads strategy + sub-agent outputs, creates concrete trade plan — *Validated in Phase 02: agent-layer*
- [x] Sub-agent: Trade Reviewer — post-trade analysis of successes and failures — *Validated in Phase 02: agent-layer*
- [x] Strategy system: Markdown strategy doc that Claude builds from scratch and evolves after each cycle — *Validated in Phase 03: strategy-evolution*
- [x] Sub-agent: Strategy Updater — reads Reviewer output, incrementally updates strategy.md, commits changes — *Validated in Phase 03: strategy-evolution*

### Active
- [ ] Strategy system: Configurable parameters (edge thresholds, Kelly fraction, filters) that agent can adjust
- [ ] Reporting: Per-cycle markdown reports with trade analysis, reasoning, and results
- [x] Scheduling: Configurable job frequency (hourly, daily, etc.) triggering full trading cycles — *Validated in Phase 04: scheduling-and-safety-hardening*
- [x] Paper trading mode as default with path to live trading — *Validated in Phase 01: instrument-layer*
- [x] Persistent state: Trade history, position tracking, strategy evolution history — *Validated in Phase 01: instrument-layer*
- [x] Safety gates: Live trading gate with paper P&L verification, 401 credential refresh, order normalization — *Validated in Phase 04: scheduling-and-safety-hardening*

### Out of Scope

- Web UI or dashboard — CLI/file-based only
- Real-time streaming — batch cycles on schedule
- Multi-exchange support — Polymarket only
- Backtesting engine — learn from live paper trading instead
- Human approval per trade — fully autonomous after configuration

## Context

**Existing codebase (reference material):**
An earlier version exists in this repo with working implementations of: Gamma API market discovery, OpenAI GPT-4o market analysis, Kelly criterion sizing, paper/live trade execution via py-clob-client, SQLite persistence, and portfolio management. This code should be reviewed and good solutions cherry-picked, but the new system is a fresh build with a fundamentally different architecture.

**Key existing code worth reviewing:**
- `market_discovery.py` — Gamma API integration, Market dataclass, JSON parsing for stringified fields
- `trader.py` — py-clob-client order execution, paper/live mode switching
- `portfolio.py` — position tracking, resolved market detection
- `data_store.py` — SQLite schema (trades, positions, decisions tables)
- `setup_wallet.py` — wallet generation, L2 credential derivation, token allowances
- `strategy.py` — Kelly criterion math

**External APIs:**
- Gamma API (`gamma-api.polymarket.com`) — market discovery, metadata
- CLOB API (`clob.polymarket.com`) — order placement, orderbook data
- Polygon RPC — on-chain allowances (live mode setup only)

**Architecture — two layers:**

1. **Instrument Layer (Python):** Stateless tools that do concrete things. Fetch markets. Get prices. Place orders. Track P&L. Record data. No decision-making — pure execution.

2. **Agent Layer (Claude Code CLI):** The brain. A main Claude agent that:
   - Reads its own strategy document before each cycle
   - Spawns 5 sub-agents via Task tool (Scanner, Analyst, Risk Manager, Planner, Reviewer)
   - Calls instrument layer via Bash tool
   - After each cycle: Reviewer generates report, main agent updates strategy
   - Strategy evolves like a human analyst's playbook — market selection, analysis approach, risk parameters, trade rules

**Agent cycle flow:**
```
Scheduled trigger
  → Main Agent reads strategy.md
  → Planner creates trade plan from strategy + market conditions
  → Scanner finds candidate markets (calls instrument tools)
  → Analyst evaluates each candidate (probability estimation)
  → Risk Manager sizes positions (portfolio context)
  → Main Agent executes trades (calls instrument tools)
  → Reviewer analyzes results, writes cycle report
  → Main Agent updates strategy.md based on learnings
```

**Strategy evolution:**
Strategy starts blank. After each cycle, Claude analyzes what worked and what didn't. Over time, the strategy document grows to cover: which market types to target/avoid, how to weigh analysis factors, risk parameter adjustments, entry/exit rules. The goal is observable improvement in paper trading profitability.

## Constraints

- **Tech stack**: Python 3.12 for instrument layer, Claude Code CLI for agent layer
- **Agent runtime**: Claude Code sessions spawning sub-agents via Task tool, calling Python via Bash
- **Trading API**: Polymarket CLOB via py-clob-client
- **Analysis**: Claude sub-agents (not OpenAI) for market analysis
- **Persistence**: SQLite for trade data, markdown files for strategy/reports
- **Safety**: Paper trading default. Never live without explicit user configuration.
- **Existing code**: Review and cherry-pick, but don't inherit the old architecture

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Two-layer architecture (instrument + agent) | Clean separation of execution tools from decision-making intelligence | ✓ Instrument layer shipped (Phase 01) |
| Claude Code CLI as agent runtime | Native sub-agent spawning via Task tool, Bash for instrument calls | — Pending |
| Multi-agent (5 sub-agents) | Specialization — each agent focuses on one concern like a team | — Pending |
| Strategy from scratch | Avoid encoding human biases; let agent discover what works | ✓ 4-domain strategy.md + core-principles.md (Phase 03) |
| Fresh codebase | Old architecture doesn't support agent layer; cherry-pick good code | ✓ V1 deleted, v2 lib/tools/ live (Phase 01) |
| Per-cycle markdown reports | Human-readable audit trail; agent reads own history for learning | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd:transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-03-27 after Phase 04 completion — scheduling and safety hardening shipped (cron scheduling, live trading gate, 401 credential retry, comprehensive safety tests)*
