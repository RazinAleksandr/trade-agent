# Project Research Summary

**Project:** Polymarket Autonomous Trading Agent — Multi-Agent Rebuild
**Domain:** Autonomous prediction market trading with Claude Code multi-agent architecture
**Researched:** 2026-03-25 / 2026-03-26
**Confidence:** HIGH

## Executive Summary

This project rebuilds the existing Polymarket trading agent from a monolithic Python loop (single OpenAI GPT-4o analyzer) into a multi-agent system orchestrated by Claude Code. The new architecture separates concerns into two distinct layers: a stateless Python instrument layer (Bash-callable CLI tools) and an intelligent agent layer (main Claude orchestrator + 5 specialized sub-agents: Scanner, Analyst, Risk Manager, Planner, Reviewer). This pattern is directly validated by academic research (TradingAgents, arXiv 2412.20138) showing multi-agent specialization outperforms single-agent approaches for trading decisions. The existing codebase is a strong foundation — its market discovery, trade execution, portfolio tracking, and SQLite persistence modules are all cherry-pick candidates, not rewrites.

The recommended approach builds bottom-up: instrument layer first (stateless Python CLI tools), then sub-agent definitions, then main agent orchestration, then scheduling and strategy evolution. The most important architectural decision is keeping ALL decision logic out of the instrument layer — tools return raw data (JSON to stdout), the agent layer reasons about it. Strategy parameters live in `state/strategy.md` (a markdown file the agent reads and updates), not in config files, enabling autonomous strategy evolution. Sub-agents must output structured JSON schemas, not prose summaries, or critical trading information (liquidity warnings, spread data) will be silently dropped at handoffs.

The two critical risks are financial. First, runaway token cost: a 5-agent cycle analyzing 20 markets costs $1-3 per run; without `--max-turns` guards and per-cycle budget monitoring, a first unattended run can exhaust monthly API quota. Second, the paper-to-live gap: the existing paper trading mode assumes perfect fills at mid-price, but real Polymarket bid-ask spreads of 5-15% on low-liquidity markets turn measured paper edge into negative live returns. Both risks are solvable at the instrument layer build phase before any agent code runs.

## Key Findings

### Recommended Stack

The agent layer runs entirely on Claude Code CLI and the `claude-agent-sdk` Python package (v0.1.50). Claude Code's native Task tool handles sub-agent spawning without any external orchestration framework — no LangChain, no Celery, no custom message queues. APScheduler (v3.11.2) drives cycle scheduling as a Python daemon. The OpenAI SDK is removed entirely: Claude sub-agents replace GPT-4o for market analysis, using web search via Claude's built-in Bash/tool capabilities rather than OpenAI's Responses API. All existing Polymarket-specific libraries (`py-clob-client` v0.34.6, `requests`, `web3`, `eth-account`) are retained unchanged.

**Core technologies:**
- **Claude Code CLI + Task tool**: Agent layer runtime — spawns sub-agents natively, no framework overhead
- **`claude-agent-sdk` v0.1.50**: Python → agent bridge for APScheduler-triggered cycle invocation
- **Python 3.12 + existing instrument modules**: Stateless CLI tools for all API/DB operations
- **SQLite3 with WAL mode**: Durable state; WAL mode required for safe concurrent reads from multiple sub-agents
- **Markdown files (`state/strategy.md`, `state/reports/`)**: Agent-owned persistent memory, human-inspectable, diffable in git
- **APScheduler v3.11.2**: Cron-style scheduling; use 3.x branch (4.x is not production-ready)

**What to drop:**
- `openai` SDK — Claude sub-agents replace GPT-4o entirely
- OpenAI Responses API `web_search` tool — Claude's Bash tool handles research
- LangChain / LangGraph — unnecessary over Claude Code's native orchestration

### Expected Features

**Must have (table stakes — system cannot trade without these):**
- Market discovery and filtering via Gamma API (existing `market_discovery.py` is the reference)
- Probability estimation per market via Analyst sub-agent with web search
- Edge calculation (estimated probability minus market price, threshold-gated)
- Kelly criterion position sizing at quarter-Kelly (0.25x) for conservative drawdown control
- Paper trading mode as default with explicit opt-in for live
- Order execution via `py-clob-client` (paper + live)
- Position tracking and P&L (existing `portfolio.py` is the reference)
- Persistent trade history in SQLite
- Configurable parameters (edge threshold, Kelly fraction, max position, max exposure)
- Cycle scheduling and graceful shutdown

**Should have (differentiators that deliver the autonomous improvement value):**
- 5 specialized sub-agents (Scanner, Analyst, Risk Manager, Planner, Reviewer) via Claude Code Task tool
- Self-evolving `state/strategy.md` — agent reads at cycle start, updates at cycle end
- Per-cycle markdown reports written by Reviewer sub-agent (`state/reports/cycle_YYYYMMDD.md`)
- Structured JSON output schemas for all sub-agents (not prose — prevents critical info loss)
- Strategy version history in git (makes drift auditable)
- Confidence-weighted position sizing (Analyst sub-agent outputs confidence level)

**Defer to v2+:**
- Market correlation awareness in Risk Manager (needs large enough portfolio to matter)
- Live trading mode hardening (requires positive paper P&L with spread simulation)
- Bull/Bear researcher debate within Analyst (only needed if probability estimates show high variance)
- Enhanced market filtering heuristics (only needed if Scanner produces too many low-quality candidates)
- Market analysis result caching (only needed when 30+ candidate markets per cycle slows analysis)

### Architecture Approach

The system is cleanly split into four layers: (1) Scheduler (cron/APScheduler) triggers the main agent via `claude -p`; (2) Agent layer — main orchestrator plus 5 sub-agents defined as `.claude/agents/*.md` files, communicating through context-forward prompt injection, not shared files; (3) Instrument layer — stateless Python CLI tools in `tools/` that output JSON to stdout and have zero decision logic; (4) Persistent state — `trading.db` (SQLite), `state/strategy.md`, and `state/reports/`. Sub-agents are defined in `.claude/agents/` with YAML frontmatter specifying allowed tools; Claude Code auto-discovers them. The main agent passes ALL necessary context to each sub-agent at dispatch time because sub-agents cannot access the main agent's conversation history.

**Major components:**
1. **Scheduler (`run_cycle.sh` + cron/APScheduler)** — triggers `claude -p "Run trading cycle"` at configured intervals; session is ephemeral per cycle
2. **Main Agent (`.claude/CLAUDE.md`)** — reads `strategy.md`, dispatches sub-agents via Task tool, executes trade plan, updates strategy; the only component that writes to `strategy.md`
3. **5 Sub-agents (`.claude/agents/`)** — Scanner (market discovery), Analyst (probability estimation), Risk Manager (Kelly sizing + portfolio risk), Planner (strategy → concrete trade plan), Reviewer (post-cycle analysis + report writing)
4. **Instrument Layer (`tools/`)** — stateless CLI tools: `discover_markets.py`, `get_price.py`, `get_orderbook.py`, `execute_trade.py`, `get_portfolio.py`, `record_trade.py`, `get_history.py`; all cherry-picked from existing codebase
5. **Persistent State** — `trading.db` (WAL mode), `state/strategy.md` (agent memory), `state/reports/` (audit trail)

### Critical Pitfalls

1. **Runaway token cost** — A 5-agent cycle analyzing 20 markets costs $1-3; without `--max-turns` (recommended: 10-15 per sub-agent) and per-cycle token budget logging, first unattended run can exhaust monthly quota. Set these limits before any unattended execution.

2. **Order precision rejection causing silent trade failures** — Kelly criterion produces arbitrary floats; CLOB API rejects orders where `size × price` exceeds 4 decimal places, and `py-clob-client` may swallow these as warnings. Implement `normalize_order(price, size)` in the instrument layer before building the agent layer.

3. **Sub-agent context loss at handoff** — Without structured output schemas, sub-agents compress prose summaries and drop critical caveats (e.g., "spread is 15%"). Every sub-agent must output a defined JSON schema; the main agent must validate it before using it.

4. **Strategy drift after many cycles** — Agent rewrites `strategy.md` based on recent correlation patterns, not causation. Lock a "Core Principles" section at the top the agent cannot modify; require minimum 5-confirmation evidence before elevating a hypothesis to a rule; commit `strategy.md` to git after every update.

5. **Paper-to-live gap** — Existing paper mode assumes perfect fills at mid-price; 5-15% spreads on low-liquidity markets convert positive paper P&L to negative live returns. Simulate spread in paper mode by pricing buys at ask and sells at bid using live order book data, even in paper mode.

## Implications for Roadmap

Based on the dependency graph in ARCHITECTURE.md and pitfall-to-phase mapping in PITFALLS.md, the natural build order is bottom-up across 4 phases.

### Phase 1: Instrument Layer Foundation

**Rationale:** Everything depends on CLI tools existing and being callable via Bash. Agent layer cannot be built or tested without working instrument tools. Multiple pitfalls (order precision, ghost portfolio, paper-to-live gap) must be fixed at this layer before any agent code runs — fixing them later is significantly more costly.
**Delivers:** Complete set of stateless Python CLI tools; hardened paper trading with spread simulation; WAL-mode SQLite; order normalization; working `get_portfolio.py` with CLOB reconciliation.
**Addresses:** Market discovery, edge calculation, Kelly sizing, paper trade execution, portfolio tracking, persistent trade history (all table-stakes features).
**Avoids:** Order precision rejection (implement `normalize_order`), ghost portfolio (WAL mode + reconciliation), paper-to-live gap (spread simulation), authentication expiry (re-derive credentials at each cycle start).
**Research flag:** Standard patterns — existing codebase provides working reference; no phase research needed.

### Phase 2: Agent Layer — Sub-Agents and Orchestration

**Rationale:** Sub-agents can only be built once instrument tools exist to test against. This phase replaces GPT-4o with Claude Analyst sub-agent and introduces the full 5-agent specialization. Output schemas must be designed before any sub-agents write code — they are the most important design decision in the architecture.
**Delivers:** All 5 sub-agent definitions (`.claude/agents/`), main agent cycle instructions, working end-to-end paper trading cycle with multi-agent orchestration, structured JSON output schemas for every sub-agent.
**Uses:** Claude Code CLI Task tool, `claude-agent-sdk` for scheduled invocation, `run_cycle.sh` entry point.
**Implements:** Context-forward dispatch pattern, per-cycle reports written by Reviewer, token cost monitoring and `--max-turns` guards.
**Avoids:** Runaway token cost (max_turns before first unattended run), sub-agent context loss (output schemas at design time), prompt injection (input sanitization for market titles/descriptions from Gamma API).
**Research flag:** May benefit from phase research — Claude Code Task tool sub-agent invocation patterns, output schema validation, `--max-turns` behavior are niche topics with limited community documentation.

### Phase 3: Strategy Evolution System

**Rationale:** Strategy evolution requires a stable cycle producing reliable reports (Phase 2). Building the evolution system before the cycle is stable produces a moving target. This phase adds the feedback loop that makes the system self-improving.
**Delivers:** Structured `state/strategy.md` template with locked Core Principles section, git-committed strategy versioning after each update cycle, Reviewer sub-agent producing structured cycle reports, strategy hypothesis vs. confirmed rule tier system.
**Avoids:** Strategy drift (locked principles section, git history, evidence thresholds), free-form strategy decay (structured format enforced from day 1).
**Research flag:** No phase research needed — pattern is well-defined in ARCHITECTURE.md with concrete structure recommendations.

### Phase 4: Scheduling, Hardening, and Live Trading Gate

**Rationale:** Scheduling and live trading gate are the last pieces, added once the cycle is stable and strategy evolution is producing useful signal. The live trading gate is an explicit phase, not a config flag, to prevent premature live trading.
**Delivers:** APScheduler or cron configuration, health-check at cycle start, credential refresh on 401, explicit live trading gate (CLI flag + confirmation prompt + minimum paper cycle requirement), complete smoke test suite.
**Avoids:** Authentication credential expiry (refresh logic), paper-to-live switch safety (explicit gate), accidental live trading (two-factor enable: CLI flag + env var).
**Research flag:** No phase research needed — scheduling patterns are standard; live trading gate design is fully specified in PITFALLS.md.

### Phase Ordering Rationale

- Phases 1-4 are strictly ordered by dependency: tools before agents, agents before strategy evolution, stable cycle before scheduling.
- The anti-pattern of building agent layer before instrument layer is explicitly called out in ARCHITECTURE.md — agents have no execution capability without tools.
- Fixing pitfalls at the earliest possible phase is cheaper: order normalization costs 1 function in Phase 1; discovering the bug in Phase 3 requires debugging across 3 layers.
- Phase 3 (strategy evolution) is intentionally not part of Phase 2 MVP to avoid building the feedback system before the underlying cycle is validated.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 2:** Claude Code Task tool sub-agent invocation with `--max-turns` and structured output validation is a niche pattern. The official docs cover basics but not edge cases (sub-agent timeout behavior, error propagation, Task tool return format). Worth a phase-research pass before detailed task breakdown.

Phases with standard patterns (skip research-phase):
- **Phase 1:** Instrument layer is largely extraction and hardening of existing codebase. Patterns are well-documented; existing working code is the primary reference.
- **Phase 3:** Strategy evolution structure is fully specified in ARCHITECTURE.md with concrete markdown templates.
- **Phase 4:** APScheduler scheduling and credential refresh patterns are standard and well-documented.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI on 2026-03-25; Claude Code CLI patterns verified against official docs; existing codebase provides working Polymarket integration reference |
| Features | MEDIUM-HIGH | Table-stakes features HIGH (direct domain knowledge + existing codebase); multi-agent feature specifics MEDIUM (LLM agent trading is an emerging field, limited production case studies) |
| Architecture | HIGH | Claude Code sub-agent patterns verified from official docs; component boundaries confirmed by TradingAgents research; existing codebase integration points are working and tested |
| Pitfalls | HIGH for API pitfalls, MEDIUM for agent pitfalls | Polymarket-specific pitfalls (precision, auth, API quirks) from official GitHub issues; multi-agent failure modes from academic research + official Claude docs, with some inference |

**Overall confidence:** HIGH

### Gaps to Address

- **Sub-agent output schema validation mechanics:** How the main agent validates sub-agent JSON output and requests reformatting is not fully documented. Need to determine whether this is handled by main agent prompt instructions or a validation tool in the instrument layer. Validate during Phase 2 planning.
- **`--max-turns` interaction with sub-agent spawning:** Unclear whether `--max-turns` on the main agent session counts sub-agent turns or only main agent turns. This affects token budget calculations. Verify against official docs or empirically during Phase 2 development.
- **Market analysis caching feasibility:** The PITFALLS.md recommends caching analysis results when price is within 2% and resolution date unchanged. The instrument layer would need a cache store; unclear whether SQLite or a separate JSON file is more appropriate. Decide during Phase 1 design.
- **Gamma API rate limits:** Not documented in research files. May need empirical testing to determine how many markets can be fetched per minute before rate limiting, which affects the Scanner sub-agent's discovery batch size.

## Sources

### Primary (HIGH confidence)
- `https://code.claude.com/docs/en/sub-agents` — Sub-agent file format, frontmatter, tool restrictions, model selection
- `https://code.claude.com/docs/en/agent-teams` — Agent teams vs sub-agents, token costs, communication model
- `https://code.claude.com/docs/en/headless` — Claude Code `-p` flag, `--allowedTools`, `--bare` mode
- `https://platform.claude.com/docs/en/agent-sdk/python` — `claude-agent-sdk` Python API
- `https://github.com/Polymarket/py-clob-client` — Official Polymarket Python CLOB client
- `https://github.com/Polymarket/py-clob-client/issues` — Precision errors, auth issues, minimum size constraints
- Existing codebase (`trader.py`, `market_discovery.py`, `data_store.py`, `CONCERNS.md`) — Working patterns and known bugs
- PyPI (py-clob-client, claude-agent-sdk, anthropic, APScheduler) — Version verification 2026-03-25

### Secondary (MEDIUM confidence)
- TradingAgents arXiv 2412.20138 — Multi-agent specialization outperforms single-agent for trading; confirms 5-agent role structure
- TradingGroup arXiv 2508.17565 — Self-reflection patterns in multi-agent trading systems
- TradeTrap arXiv 2512.02261 — Epistemic hallucination, phantom portfolio in LLM trading agents
- `https://galileo.ai/blog/multi-agent-llm-systems-fail` — Coordination failures, context loss at handoffs
- `https://prassanna.io/blog/agent-drift/` — Context drift, recency bias in long-running agents
- `https://www.agentpatterns.tech/en/failures/infinite-loop` — Infinite loop failure modes
- `https://docs.polymarket.com/developers/gamma-markets-api/overview` — Gamma API endpoints, response structure
- `https://fast.io/resources/ai-agent-job-scheduling/` — File-based state management for scheduled agents

### Tertiary (LOW confidence)
- `https://www.coindesk.com/tech/2026/03/15/ai-agents-are-quietly-rewriting-prediction-market-trading` — Competitive landscape context
- `https://medium.com/@stevenn.hansen/best-polymarket-trading-bots-for-automated-prediction-market-strategies-in-2026-bf06df02823b` — Competitor feature analysis (Polystrat, OpenClaw)

---
*Research completed: 2026-03-26*
*Ready for roadmap: yes*
