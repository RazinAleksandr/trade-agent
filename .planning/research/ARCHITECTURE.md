# Architecture Research

**Domain:** Multi-agent autonomous trading system (Claude Code CLI + Python instrument layer)
**Researched:** 2026-03-25
**Confidence:** HIGH (Claude Code docs verified from official source; trading system patterns from academic frameworks and official Polymarket agents repo)

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        SCHEDULING LAYER                                  │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │   cron / launchd trigger → claude -p "run trading cycle" [...]  │    │
│  └────────────────────────────────┬────────────────────────────────┘    │
└───────────────────────────────────│─────────────────────────────────────┘
                                    │
┌───────────────────────────────────▼─────────────────────────────────────┐
│                        AGENT LAYER (Claude Code CLI)                     │
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────┐      │
│  │                    MAIN AGENT (Orchestrator)                    │      │
│  │  • Reads strategy.md before each cycle                         │      │
│  │  • Dispatches sub-agents via Task tool                         │      │
│  │  • Calls instrument layer via Bash tool                        │      │
│  │  • Synthesizes outputs → executes trades → writes reports      │      │
│  │  • Updates strategy.md after each cycle                        │      │
│  └──────┬──────────┬─────────────┬──────────────┬────────────────┘      │
│         │          │             │              │                         │
│  ┌──────▼──┐ ┌─────▼────┐ ┌─────▼──────┐ ┌────▼────────┐               │
│  │ Scanner │ │ Analyst  │ │ Risk Mgr   │ │  Planner    │               │
│  │sub-agent│ │sub-agent │ │ sub-agent  │ │  sub-agent  │               │
│  └─────────┘ └──────────┘ └────────────┘ └─────────────┘               │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                   Reviewer sub-agent (post-cycle)               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────┬───────────────────────────────────┘
                                      │ Bash tool calls
┌─────────────────────────────────────▼───────────────────────────────────┐
│                      INSTRUMENT LAYER (Python CLI tools)                 │
│                                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │
│  │   discover   │  │  get_price   │  │  get_book    │  │    trade    │  │
│  │   markets    │  │  /orderbook  │  │  snapshot    │  │  execute   │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬────┘  │
│         │                 │                  │                  │        │
│  ┌──────▼──────────────────▼──────────────────▼──────────────────▼────┐  │
│  │                         portfolio / db                              │  │
│  │              get_portfolio / record_trade / get_history             │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────┬──────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                        EXTERNAL APIS                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │  Gamma API       │  │  CLOB API        │  │  Polygon RPC          │   │
│  │  (market data)   │  │  (order book /   │  │  (allowances, live)   │   │
│  │                  │  │   execution)     │  │                       │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────▼──────────────────────────────────────┐
│                        PERSISTENT STATE                                   │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐   │
│  │   trading.db     │  │  strategy.md     │  │  reports/            │   │
│  │  (SQLite:        │  │  (living doc     │  │  cycle_YYYYMMDD.md   │   │
│  │  trades,         │  │  agent reads     │  │  per-cycle analysis  │   │
│  │  positions,      │  │  and updates)    │  │  written by Reviewer │   │
│  │  decisions)      │  │                  │  │                      │   │
│  └──────────────────┘  └──────────────────┘  └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| Scheduler (cron/launchd) | Trigger agent cycle at configured frequency | Main Agent (via claude -p) |
| Main Agent | Orchestrate full cycle, synthesize sub-agent outputs, execute trades, update strategy | All sub-agents, Instrument Layer, Persistent State |
| Scanner sub-agent | Find candidate markets from Gamma API meeting initial criteria | Instrument Layer (discover_markets tool), Main Agent |
| Analyst sub-agent | Deep-dive individual candidates for probability estimation | Instrument Layer (get_price, get_orderbook tools), Main Agent |
| Risk Manager sub-agent | Evaluate current portfolio risk, size positions with Kelly criterion | Instrument Layer (get_portfolio tool), Main Agent |
| Planner sub-agent | Synthesize strategy + sub-agent outputs into concrete ordered trade plan | Main Agent (receives strategy.md + outputs as context) |
| Reviewer sub-agent | Post-cycle analysis of what worked, what failed, and why | Instrument Layer (get_history tool), Main Agent |
| Instrument Layer (Python) | Stateless execution tools — no decision logic | External APIs, SQLite |
| strategy.md | Living strategy document — agent reads it to inform decisions, updates it to evolve | Main Agent (read/write) |
| reports/ directory | Per-cycle markdown audit trail — Reviewer writes, future cycles can reference | Reviewer sub-agent (write), Main Agent (reference) |
| trading.db (SQLite) | Durable state: trade history, positions, decisions | Instrument Layer |

## Recommended Project Structure

```
polymarket-agent/
├── tools/                  # Instrument layer — Python CLI tools
│   ├── discover_markets.py # Gamma API discovery, returns JSON
│   ├── get_price.py        # Single market price lookup
│   ├── get_orderbook.py    # CLOB orderbook snapshot
│   ├── execute_trade.py    # Paper/live order execution
│   ├── get_portfolio.py    # Current positions, exposure, P&L
│   ├── record_trade.py     # Write trade record to DB
│   ├── get_history.py      # Query trade/decision history
│   └── shared/             # Shared utilities (not tools)
│       ├── db.py           # SQLite connection + schema
│       ├── config.py       # Env loading (from existing codebase)
│       └── clob_client.py  # py-clob-client wrapper
├── .claude/
│   └── agents/             # Sub-agent definitions (YAML frontmatter + system prompt)
│       ├── scanner.md
│       ├── analyst.md
│       ├── risk-manager.md
│       ├── planner.md
│       └── reviewer.md
├── state/
│   ├── strategy.md         # Living strategy document (agent-owned)
│   └── reports/            # Per-cycle reports (reviewer-written)
│       └── cycle_YYYYMMDD_HHMMSS.md
├── run_cycle.sh            # Entrypoint: claude -p with flags for scheduling
├── trading.db              # SQLite database (gitignored)
├── tests/                  # Smoke tests for instrument layer
└── .env                    # Secrets (gitignored)
```

### Structure Rationale

- **tools/**: Each tool is a standalone Python script invoked via Bash tool. Callable as `python tools/discover_markets.py --limit 20 --min-volume 1000`. JSON output to stdout for easy parsing by Claude. No decision logic.
- **.claude/agents/**: Sub-agent definitions loaded by Claude Code automatically. YAML frontmatter specifies name, description (routing hint for main agent), allowed tools, and system prompt.
- **state/**: Human-inspectable persistent state. strategy.md is owned by the agent; reports/ is the audit trail.
- **run_cycle.sh**: Single entry point called by cron — `claude -p "Run a complete trading cycle following your strategy" --allowedTools "Bash,Read,Write,Agent"`. Keeps scheduling configuration separate from agent logic.

## Architectural Patterns

### Pattern 1: Stateless Tools, Stateful Agent

**What:** Instrument layer tools are pure input/output — given arguments, they call APIs or query DB, return JSON, and exit. All state lives in files (strategy.md, reports/) and SQLite. The agent holds the intelligence.

**When to use:** Always. This is the core principle that makes the two-layer architecture work.

**Trade-offs:** Requires explicit context passing from Main Agent to sub-agents (each sub-agent gets only what's in its prompt — sub-agents cannot share state directly).

**Example:**
```python
# tools/discover_markets.py — pure tool, no agent logic
import json, argparse
from shared.config import load_config
from market_discovery import fetch_active_markets  # cherry-picked from existing code

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-volume", type=float, default=1000)
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()
    markets = fetch_active_markets(min_volume=args.min_volume, limit=args.limit)
    print(json.dumps([m.__dict__ for m in markets], indent=2))

if __name__ == "__main__":
    main()
```

Main Agent calls: `python tools/discover_markets.py --min-volume 5000 --limit 15`

### Pattern 2: Context-Forward Sub-Agent Dispatch

**What:** When Main Agent spawns a sub-agent via Task tool, it passes ALL needed context in the prompt string — file paths, prior outputs, key parameters. Sub-agents have their own context window and cannot read Main Agent's conversation history.

**When to use:** Every sub-agent invocation.

**Trade-offs:** Makes prompts verbose; pays for itself in isolation and focus. Context size is controllable (pass summaries not full outputs).

**Example (Main Agent internal reasoning):**
```
Dispatch to Analyst sub-agent with prompt:
"Analyze these 5 markets for trading opportunities.
Current strategy context: [paste relevant section of strategy.md]
Markets to analyze: [paste JSON from Scanner output]
For each market, call: python tools/get_price.py --market-id <id>
Return your analysis as JSON: {market_id, estimated_prob, market_prob, edge, confidence, reasoning}"
```

### Pattern 3: Strategy Document as Persistent Agent Memory

**What:** strategy.md is a markdown file the Main Agent reads at cycle start and updates at cycle end. It is not code — it is the agent's accumulated wisdom about what trading approaches work on this platform. Starts blank; grows over cycles.

**When to use:** Every cycle start (read) and end (update).

**Trade-offs:** Human-readable and inspectable, but text-based so structured data (thresholds, parameters) must be represented in markdown tables or YAML blocks within the doc. Requires discipline about format to prevent drift.

**Structure recommendation:**
```markdown
# Trading Strategy

## Market Selection Criteria
[Agent fills in: what market types to target, avoid, etc.]

## Analysis Approach
[Agent fills in: how to weight different probability signals]

## Risk Parameters
| Parameter | Value | Last Changed | Reason |
|-----------|-------|-------------|--------|
| min_edge  | 0.12  | 2026-03-20  | tightened after 3 false signals |

## Rules
[Agent fills in: hard rules derived from experience]

## What Has Worked
[Agent fills in]

## What Has Not Worked
[Agent fills in]
```

### Pattern 4: Per-Cycle Markdown Reports as Feedback Loop

**What:** After each cycle, the Reviewer sub-agent writes `state/reports/cycle_YYYYMMDD_HHMMSS.md` containing trade analysis, prediction vs outcome comparison for resolved markets, and concrete lessons. Main Agent reads recent reports when updating strategy.

**When to use:** Every cycle, post-execution.

**Trade-offs:** File accumulation over time — simple `ls state/reports/ | tail -5` gives last 5 cycles. Long-term analysis requires reading multiple files, which is tractable via Bash tool.

## Data Flow

### Full Trading Cycle Flow

```
Scheduler triggers claude -p "Run trading cycle" [flags]
  │
  ▼
Main Agent: reads strategy.md
  │
  ▼
[PARALLEL DISPATCH - Sub-agents run concurrently]
  ├── Scanner sub-agent
  │     calls: python tools/discover_markets.py
  │     returns: JSON list of candidate markets
  │
  └── [if prior cycles exist]
      Reviewer sub-agent reads last cycle report
      returns: summary of recent performance
  │
  ▼
Main Agent: receives Scanner output
  │
  ▼
[SEQUENTIAL DISPATCH]
Analyst sub-agent (once per candidate batch)
  │  calls: python tools/get_price.py for each market
  │  calls: python tools/get_orderbook.py for each market
  │  returns: JSON analysis {market_id, estimated_prob, edge, confidence, reasoning}
  ▼
Risk Manager sub-agent
  │  calls: python tools/get_portfolio.py
  │  applies Kelly criterion from strategy.md params
  │  returns: JSON sizing {market_id, recommended_size_usdc, max_exposure_remaining}
  ▼
Planner sub-agent
  │  receives: strategy.md + Analyst output + Risk Manager output
  │  returns: ordered trade plan [{market_id, side, size, price, rationale}]
  ▼
Main Agent: executes trade plan
  │  calls: python tools/execute_trade.py for each trade
  │  paper mode: records locally; live mode: posts to CLOB API
  ▼
Main Agent: checks portfolio
  │  calls: python tools/get_portfolio.py
  ▼
Reviewer sub-agent
  │  calls: python tools/get_history.py --last-n 20
  │  compares resolved market outcomes to prior predictions
  │  writes: state/reports/cycle_YYYYMMDD_HHMMSS.md
  ▼
Main Agent: updates strategy.md
  │  reads Reviewer's report
  │  amends strategy.md: parameters, rules, lessons
  ▼
Cycle complete. Scheduler sleeps until next trigger.
```

### State Management

```
Per-cycle ephemeral (in agent context window):
  Scanner output → passed to Analyst prompt
  Analyst output → passed to Risk Manager + Planner prompt
  Risk Manager output → passed to Planner prompt
  Planner output → used by Main Agent for execution

Persistent cross-cycle:
  trading.db ← written by execute_trade.py, get_portfolio.py
  strategy.md ← updated by Main Agent after each cycle
  state/reports/ ← written by Reviewer each cycle

Cross-cycle data access patterns:
  Main Agent reads strategy.md at start of every cycle
  Reviewer reads trading.db via get_history.py to compare predictions vs outcomes
  Main Agent reads last N reports (via Bash: cat state/reports/*.md | tail -200) before strategy update
```

## Build Order Implications

The dependency graph dictates a bottom-up build order:

**Phase 1 — Instrument Layer Foundation**
Build first because everything else depends on these tools existing and being callable via Bash.
- shared/db.py, shared/config.py (from existing code)
- discover_markets.py (from existing market_discovery.py)
- get_price.py, get_orderbook.py
- execute_trade.py (paper mode first; live mode later)
- get_portfolio.py, record_trade.py, get_history.py

**Phase 2 — Sub-Agent Definitions**
Build after instrument tools exist to test sub-agents against real tool outputs.
- .claude/agents/scanner.md (depends on discover_markets tool)
- .claude/agents/analyst.md (depends on get_price, get_orderbook)
- .claude/agents/risk-manager.md (depends on get_portfolio)
- .claude/agents/planner.md (depends on prior 3 sub-agents working)
- .claude/agents/reviewer.md (depends on get_history, execute_trade)

**Phase 3 — Main Agent Orchestration + Strategy System**
Build after sub-agents are tested individually.
- run_cycle.sh (entry point)
- strategy.md initial template
- Main Agent CLAUDE.md instructions for cycle behavior
- Integration test: full cycle end-to-end in paper mode

**Phase 4 — Scheduling + Reporting**
Build last when cycle is stable.
- Cron/launchd configuration
- Report format standardization
- Strategy evolution validation

## Anti-Patterns

### Anti-Pattern 1: Decision Logic in Instrument Tools

**What people do:** Add market analysis, Kelly sizing, or filtering logic directly in Python tool scripts.

**Why it's wrong:** Tools become opinionated. The agent cannot override their behavior. Defeats the purpose of the agent layer. Makes the system a more elaborate version of the old architecture.

**Do this instead:** Tools return raw data (prices, orderbook, portfolio state). All decision logic lives in sub-agent prompts or Main Agent reasoning.

### Anti-Pattern 2: Sharing State Between Sub-Agents Via Files

**What people do:** Scanner sub-agent writes `/tmp/candidates.json`, Analyst sub-agent reads it.

**Why it's wrong:** Creates implicit coupling and race conditions. Makes sub-agent execution order fragile. File paths must be coordinated externally.

**Do this instead:** Main Agent receives each sub-agent's output and explicitly passes relevant context to the next sub-agent in the Task prompt. Ephemeral context, not shared files.

### Anti-Pattern 3: Encoding Strategy in Python Config

**What people do:** Put edge thresholds, Kelly fractions, and market filters in `.env` or `config.py`.

**Why it's wrong:** Removes strategy evolution ability from the agent. The agent cannot update a Python config file safely. Defeats the goal of autonomous strategy improvement.

**Do this instead:** Parameters live in strategy.md as a markdown table. Agent reads and updates them naturally. Only secrets and infrastructure config go in `.env`.

### Anti-Pattern 4: Monolithic Orchestrator Prompt

**What people do:** Put all logic in a single enormous main agent prompt that tries to do discovery, analysis, sizing, and execution inline.

**Why it's wrong:** Context window exhaustion on large market lists. No specialization. Hard to debug which step went wrong. Analysis quality degrades when same context holds everything.

**Do this instead:** Delegate to specialized sub-agents. Each sub-agent gets a focused context. Main Agent only receives summaries and makes final calls.

### Anti-Pattern 5: Skipping Paper Trading Validation Gate

**What people do:** Switch PAPER_TRADING=false once the code runs without errors.

**Why it's wrong:** Code running is not the same as strategy working. Live trading before strategy validation can lose real capital.

**Do this instead:** Enforce an explicit gate: strategy must show positive expected value over N paper cycles before live mode is available. Gate lives in Main Agent instructions, not just config.

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Gamma API | HTTP GET via requests in discover_markets.py | Returns stringified JSON for clobTokenIds — use json.loads() (verified in existing code) |
| CLOB API | py-clob-client in execute_trade.py | signature_type=0 for EOA; L2 credentials derived from private key; GTC limit orders |
| Polygon RPC | web3.py in setup_wallet.py (one-time only) | Only needed for live mode token allowances |
| Claude Code CLI | claude -p "prompt" --allowedTools "Bash,Read,Write,Agent" | Sub-agents defined in .claude/agents/ are auto-discovered |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Scheduler → Main Agent | OS exec: `claude -p "..."` with flags | Session per cycle; no state in claude session between cycles |
| Main Agent → Sub-agents | Task tool with full context in prompt string | Sub-agents cannot access Main Agent's conversation history |
| Main Agent → Instrument Layer | Bash tool: `python tools/xxx.py --args` | Tools output JSON to stdout; errors to stderr |
| Sub-agents → Instrument Layer | Bash tool (same as Main Agent) | Sub-agents given Bash access in their YAML frontmatter |
| Instrument Layer → SQLite | sqlite3 (stdlib) in db.py | No ORM; direct SQL for simplicity and zero deps |
| Instrument Layer → External APIs | requests, py-clob-client | Retry logic in tools; fail gracefully with exit code non-zero |

## Sources

- [Claude Code Sub-agents Official Docs](https://code.claude.com/docs/en/sub-agents) — HIGH confidence; verified frontmatter format, tool inheritance, context passing patterns
- [Claude Code Agent Teams Official Docs](https://code.claude.com/docs/en/agent-teams) — HIGH confidence; confirmed sub-agents vs agent teams distinction, communication model
- [Claude Code Headless Mode Official Docs](https://code.claude.com/docs/en/headless) — HIGH confidence; verified `claude -p` scheduling pattern, `--allowedTools`, `--bare` flag
- [TradingAgents: Multi-Agents LLM Financial Trading Framework (arXiv 2412.20138)](https://arxiv.org/abs/2412.20138) — MEDIUM confidence; academic framework confirming agent specialization patterns (Analyst, Risk, Trader roles)
- [Polymarket Official Agents Repo](https://github.com/Polymarket/agents) — HIGH confidence; confirmed Gamma API + CLOB API integration pattern, Chroma for vectorized context
- [AI Agent Job Scheduling Patterns 2026](https://fast.io/resources/ai-agent-job-scheduling/) — MEDIUM confidence; file-based state management best practices for scheduled agents

---
*Architecture research for: Multi-agent autonomous Polymarket trading system*
*Researched: 2026-03-25*
