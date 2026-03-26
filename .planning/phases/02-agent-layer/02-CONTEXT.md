# Phase 2: Agent Layer - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Multi-agent Claude Code orchestration with 5 specialized sub-agents (Scanner, Analyst, Risk Manager, Planner, Reviewer) that call Phase 1 instrument layer tools to run a complete trading cycle — discovering markets, estimating probabilities, sizing positions, executing paper trades, and writing a cycle report. Strategy evolution (Phase 3) and scheduling/safety (Phase 4) are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Orchestration Flow
- **D-01:** Sequential pipeline: Scanner -> Analyst -> Risk Manager -> Planner -> Execute -> Reviewer. Each agent receives the previous agent's output. Deterministic and debuggable.
- **D-02:** Skip and continue on sub-agent failures. Drop the failed market/step, log the failure, continue the cycle with whatever succeeded. Mirrors Phase 1 error handling pattern (safe defaults on error).
- **D-03:** Main agent is Claude Code itself with project instructions. Sub-agents are `.claude/agents/*.md` files spawned via the Task tool. Uses Claude Code's native agent infrastructure.
- **D-04:** Sub-agents pass data via JSON files in `state/`. Each agent writes its structured output to a JSON file (e.g., `state/cycles/{cycle_id}/scanner_output.json`). Next agent reads from those files. Persistent, debuggable, survives crashes.

### Analyst Debate Design
- **D-05:** Single Analyst agent call per market with a structured prompt that forces Bull case, then Bear case, then synthesizes a final probability estimate. Not two separate agents — one call that argues both sides.
- **D-06:** Analyst always uses web search for real-time context during analysis. Every market gets current information via web search tool.
- **D-07:** Analyst evaluates all markets returned by Scanner (up to `MAX_MARKETS_PER_CYCLE`, default 10). Full coverage.
- **D-08:** One market per Analyst agent call. Separate Task spawned per market. Can run in parallel via multiple Task calls. Failure on one market doesn't affect others.

### State & Report Layout
- **D-09:** State directory structure: `state/strategy.md` for strategy document, `state/reports/` for cycle reports, `state/cycles/{cycle_id}/` for intermediate sub-agent output files.
- **D-10:** Main agent reads `state/strategy.md` plus the 3 most recent cycle reports at the start of each cycle. Enough context for learning without flooding the context window.
- **D-11:** Full detail cycle reports including: markets scanned, markets analyzed (with Bull/Bear reasoning), trades taken/skipped with reasoning, position sizes, portfolio state, cycle P&L, and the agent's stated learnings.
- **D-12:** Keep all intermediate sub-agent outputs per cycle in `state/cycles/{cycle_id}/`. Full audit trail — disk is cheap, debugging is expensive.

### Claude's Discretion
- Correlation detection approach for Risk Manager (AGNT-06) — how to determine if markets are correlated
- Exact JSON schemas for inter-agent communication (AGNT-09)
- `max_turns` limits per sub-agent (AGNT-10) — empirical testing needed
- Token cost tracking implementation
- Sub-agent prompt engineering and instructions
- Exact cycle report markdown format and naming convention
- Planner sub-agent trade plan structure

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Success Criteria
- `.planning/REQUIREMENTS.md` — AGNT-01 through AGNT-10 (all Phase 2 requirements)
- `.planning/ROADMAP.md` — Phase 2 success criteria (5 acceptance tests)

### Phase 1 Decisions (instrument layer interface)
- `.planning/phases/01-instrument-layer/01-CONTEXT.md` — D-01 through D-11: tool interface (argparse, JSON stdout, errors to stderr), shared code in lib/, paper trade pricing

### API & Integration Details
- `.planning/codebase/INTEGRATIONS.md` — Gamma API, CLOB API, Polygon RPC hosts, auth patterns, contract addresses
- `docs/api-reference.md` — Gamma API endpoints, CLOB order flow, authentication details

### Codebase Architecture
- `.planning/codebase/STRUCTURE.md` — Current file layout (lib/, tools/, tests/)
- `.planning/codebase/CONVENTIONS.md` — Naming patterns, error handling, logging conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `lib/config.py` — Config dataclass with `load_config()` factory. Sub-agents call tools that load config internally.
- `lib/db.py` — DataStore with trades, positions, decisions tables. Sub-agents write via tools, main agent can read directly.
- `lib/models.py` — Market, TradeSignal, OrderResult dataclasses. Defines the data structures sub-agents work with.
- `lib/market_data.py` — Gamma API client functions (`fetch_active_markets`, `fetch_market_by_id`). Scanner agent calls `tools/discover_markets.py` which uses these.
- `lib/strategy.py` — Kelly criterion, edge calculation. Risk Manager calls `tools/calculate_kelly.py` and `tools/calculate_edge.py`.
- `lib/trading.py` — Paper + live execution functions. Execute step calls `tools/execute_trade.py`.
- `lib/portfolio.py` — Position tracking, P&L, resolved markets. Reviewer reads via `tools/get_portfolio.py`.

### Established Patterns
- Tools output JSON to stdout, errors as JSON to stderr (Phase 1 D-02, D-03)
- Each tool is single-purpose with argparse (Phase 1 D-01, D-04)
- Console logging to stderr so stdout is clean for JSON (Phase 1 state decision)
- Stateless functions — no class instances needed between calls

### Integration Points
- `tools/discover_markets.py` — Scanner agent's primary tool
- `tools/get_prices.py` — Analyst can check current prices
- `tools/calculate_edge.py` — Risk Manager evaluates edge
- `tools/calculate_kelly.py` — Risk Manager sizes positions
- `tools/execute_trade.py` — Main agent executes the trade plan
- `tools/get_portfolio.py` — Risk Manager + Reviewer check portfolio state
- `tools/check_resolved.py` — Reviewer checks for resolved markets
- `.claude/agents/` — New directory for sub-agent prompt files (Scanner, Analyst, Risk Manager, Planner, Reviewer)
- `state/` — New directory for strategy, reports, and cycle data

</code_context>

<specifics>
## Specific Ideas

- Sub-agents should be Claude Code agents in `.claude/agents/` with prompts, memory, etc. — using Claude Code's native agent infrastructure
- Main agent is Claude Code itself, orchestrating via Task tool calls to the sub-agent files
- This is NOT a Python orchestration script — the intelligence lives in Claude Code, calling Python tools via Bash

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 02-agent-layer*
*Context gathered: 2026-03-26*
