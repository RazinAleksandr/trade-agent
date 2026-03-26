# Phase 2: Agent Layer - Research

**Researched:** 2026-03-26
**Domain:** Claude Code multi-agent orchestration with sub-agents calling Python CLI tools
**Confidence:** HIGH

## Summary

Phase 2 builds the multi-agent trading cycle on top of Phase 1's instrument layer. The main Claude Code session orchestrates 5 specialized sub-agents (Scanner, Analyst, Risk Manager, Planner, Reviewer) defined as `.claude/agents/*.md` files with YAML frontmatter. Sub-agents are spawned via the Task tool (aliased as Agent in newer versions), receive structured prompts, call Phase 1 Python CLI tools via Bash, and write JSON output files to `state/cycles/{cycle_id}/`. The main agent reads these files to pass context between pipeline stages.

Claude Code v2.1.50 is installed on this machine. Sub-agents cannot spawn other sub-agents (architectural constraint). Each sub-agent gets its own context window and toolset specified in the YAML frontmatter. The `maxTurns` field in frontmatter caps agentic turns per sub-agent. Data flows through JSON files in `state/` -- persistent, debuggable, and crash-recoverable.

**Primary recommendation:** Build 5 sub-agent `.md` files in `.claude/agents/` with restricted tool access, structured prompts that instruct JSON file output, and a main orchestration prompt/script that runs the sequential pipeline. Use `maxTurns` in frontmatter to cap cost per sub-agent. Test each sub-agent independently before wiring the full pipeline.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Sequential pipeline: Scanner -> Analyst -> Risk Manager -> Planner -> Execute -> Reviewer. Each agent receives the previous agent's output. Deterministic and debuggable.
- **D-02:** Skip and continue on sub-agent failures. Drop the failed market/step, log the failure, continue the cycle with whatever succeeded. Mirrors Phase 1 error handling pattern (safe defaults on error).
- **D-03:** Main agent is Claude Code itself with project instructions. Sub-agents are `.claude/agents/*.md` files spawned via the Task tool. Uses Claude Code's native agent infrastructure.
- **D-04:** Sub-agents pass data via JSON files in `state/`. Each agent writes its structured output to a JSON file (e.g., `state/cycles/{cycle_id}/scanner_output.json`). Next agent reads from those files. Persistent, debuggable, survives crashes.
- **D-05:** Single Analyst agent call per market with a structured prompt that forces Bull case, then Bear case, then synthesizes a final probability estimate. Not two separate agents -- one call that argues both sides.
- **D-06:** Analyst always uses web search for real-time context during analysis. Every market gets current information via web search tool.
- **D-07:** Analyst evaluates all markets returned by Scanner (up to `MAX_MARKETS_PER_CYCLE`, default 10). Full coverage.
- **D-08:** One market per Analyst agent call. Separate Task spawned per market. Can run in parallel via multiple Task calls. Failure on one market doesn't affect others.
- **D-09:** State directory structure: `state/strategy.md` for strategy document, `state/reports/` for cycle reports, `state/cycles/{cycle_id}/` for intermediate sub-agent output files.
- **D-10:** Main agent reads `state/strategy.md` plus the 3 most recent cycle reports at the start of each cycle. Enough context for learning without flooding the context window.
- **D-11:** Full detail cycle reports including: markets scanned, markets analyzed (with Bull/Bear reasoning), trades taken/skipped with reasoning, position sizes, portfolio state, cycle P&L, and the agent's stated learnings.
- **D-12:** Keep all intermediate sub-agent outputs per cycle in `state/cycles/{cycle_id}/`. Full audit trail -- disk is cheap, debugging is expensive.

### Claude's Discretion
- Correlation detection approach for Risk Manager (AGNT-06) -- how to determine if markets are correlated
- Exact JSON schemas for inter-agent communication (AGNT-09)
- `max_turns` limits per sub-agent (AGNT-10) -- empirical testing needed
- Token cost tracking implementation
- Sub-agent prompt engineering and instructions
- Exact cycle report markdown format and naming convention
- Planner sub-agent trade plan structure

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| AGNT-01 | Main agent reads strategy.md at cycle start and orchestrates sub-agents via Claude Code Task tool | Claude Code Task tool with `subagent_type` pointing to custom `.claude/agents/*.md` files; `maxTurns` in frontmatter; main agent reads `state/strategy.md` via Read tool |
| AGNT-02 | Scanner sub-agent calls instrument tools to find and filter candidate markets, returns ranked list | Scanner agent with `tools: Bash, Read, Write` calling `python tools/discover_markets.py`; writes JSON to `state/cycles/{cycle_id}/scanner_output.json` |
| AGNT-03 | Analyst sub-agent deep-dives each candidate market using web search, estimates probability with confidence | Analyst agent with `tools: Bash, Read, Write, WebSearch, WebFetch`; one Task per market (D-08); parallel invocation possible |
| AGNT-04 | Analyst runs Bull/Bear debate for each market | Single Analyst prompt structured as Bull case -> Bear case -> Synthesis (D-05); prompt engineering in agent's markdown body |
| AGNT-05 | Risk Manager evaluates portfolio context, checks exposure limits, sizes positions via Kelly with confidence weighting | Risk Manager agent with `tools: Bash, Read, Write` calling `tools/get_portfolio.py`, `tools/calculate_kelly.py`, `tools/calculate_edge.py`; reads analyst outputs from state |
| AGNT-06 | Risk Manager detects correlated market exposure and adjusts sizing | Correlation detection via question/category semantic similarity analysis within the Risk Manager prompt; reduce combined sizing for correlated positions |
| AGNT-07 | Planner reads strategy + all prior outputs, creates concrete trade plan | Planner agent with `tools: Bash, Read, Write`; reads scanner/analyst/risk outputs; writes `trade_plan.json` |
| AGNT-08 | Reviewer analyzes cycle results | Reviewer agent with `tools: Bash, Read, Write`; reads trade results, portfolio state; writes cycle report markdown + `reviewer_output.json` |
| AGNT-09 | Sub-agents return structured JSON with defined schemas | Agent prompts instruct JSON file output; main agent validates structure after reading files; JSON schemas defined per agent |
| AGNT-10 | Each sub-agent has max_turns limit | `maxTurns` YAML frontmatter field in each `.claude/agents/*.md` file |

</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.12**, virtualenv at `.venv/`
- **Always run tests after changes:** `python tests/test_paper_trading.py` (legacy) and `pytest tests/` (Phase 1 suite)
- **Never commit** `.env`, `trading.db`, `trading.log`, or `.claude/`
- **Paper trading is default** -- never change `PAPER_TRADING` to `false` without explicit user request
- **Keep modules flat** -- all `.py` files in project root (but lib/ and tools/ structure from Phase 1 supersedes this)
- **All parameters in `config.py`** -- no hardcoded values in other modules
- **Secrets only in `.env`** -- loaded via `python-dotenv`, never in source code
- **Activate venv before running:** `source .venv/bin/activate`
- **GSD Workflow Enforcement** -- use GSD entry points, no direct repo edits outside workflow

## Standard Stack

### Core
| Component | Version | Purpose | Why Standard |
|-----------|---------|---------|--------------|
| Claude Code CLI | 2.1.50 | Agent runtime, Task tool for sub-agent spawning | Native infrastructure; sub-agents are `.claude/agents/*.md` files |
| Python 3.12.9 | 3.12.9 | Instrument layer tools (Phase 1) | Project requirement |
| Phase 1 CLI tools | v1 | Market discovery, pricing, Kelly, execution, portfolio | Already built and tested; agents call these via Bash |

### Supporting
| Component | Purpose | When to Use |
|-----------|---------|-------------|
| `.claude/agents/*.md` | Sub-agent definition files with YAML frontmatter | One file per agent role (Scanner, Analyst, Risk Manager, Planner, Reviewer) |
| `state/` directory | Persistent inter-agent data passing | JSON files per cycle, strategy document, cycle reports |
| `maxTurns` frontmatter | Cost control per sub-agent | Set in each agent's YAML frontmatter |
| `WebSearch` / `WebFetch` tools | Real-time market research | Analyst sub-agent only (D-06) |
| `jq` or Python JSON parsing | Validate sub-agent JSON output | Main agent validates after each sub-agent completes |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `.claude/agents/*.md` Task tool | `claude -p` via Bash | Would bypass native sub-agent infrastructure; loses context management, parallel execution, and maxTurns; more fragile |
| JSON files in `state/` | Passing data in Task prompt text | Prompt text has size limits; files are persistent, debuggable, and crash-recoverable |
| Agent teams (experimental) | Sub-agents via Task tool | Agent teams are experimental and disabled by default; Task tool is stable and sufficient for sequential pipeline |
| Python orchestration script | Claude Code as orchestrator | Decision D-03: "the intelligence lives in Claude Code, calling Python tools via Bash" -- not a Python orchestration script |

## Architecture Patterns

### Recommended Project Structure
```
.claude/agents/
  scanner.md           # Scanner sub-agent definition
  analyst.md           # Analyst sub-agent definition (Bull/Bear debate)
  risk-manager.md      # Risk Manager sub-agent definition
  planner.md           # Planner sub-agent definition
  reviewer.md          # Reviewer sub-agent definition

state/
  strategy.md          # Living strategy document (blank initially)
  reports/             # Cycle report markdown files
    cycle-{timestamp}.md
  cycles/
    {cycle_id}/        # Per-cycle intermediate outputs
      scanner_output.json
      analyst_output.json        # Array of per-market analyses
      analyst_{market_id}.json   # Individual market analysis
      risk_output.json
      trade_plan.json
      execution_results.json
      reviewer_output.json

tools/                 # Phase 1 CLI tools (already exist)
lib/                   # Phase 1 shared code (already exists)
tests/                 # Test suite
```

### Pattern 1: Sub-Agent Definition File
**What:** Each sub-agent is a markdown file with YAML frontmatter specifying name, description, tools, model, maxTurns, and the system prompt in the markdown body.
**When to use:** Every sub-agent in the pipeline.
**Example:**
```yaml
---
name: scanner
description: Scans Polymarket for tradable markets using instrument layer tools. Use when starting a trading cycle.
tools: Bash, Read, Write
model: inherit
maxTurns: 6
permissionMode: bypassPermissions
---

You are the Scanner agent for a Polymarket trading system.

## Your Task
1. Run the market discovery tool to find active markets
2. Write the results as structured JSON to the specified output path

## Tools Available
- `python tools/discover_markets.py` -- discovers active markets from Gamma API
- `python tools/get_prices.py --token-id <id>` -- gets current orderbook prices

## Output Format
Write a JSON file to the path specified in your instructions with this schema:
{
  "cycle_id": "string",
  "timestamp": "ISO 8601",
  "markets_found": number,
  "markets": [
    {
      "id": "string",
      "condition_id": "string",
      "question": "string",
      "yes_price": number,
      "no_price": number,
      "volume_24h": number,
      "liquidity": number,
      "category": "string",
      "end_date": "string",
      "yes_token_id": "string",
      "no_token_id": "string",
      "neg_risk": boolean
    }
  ]
}
```

### Pattern 2: Main Agent Orchestration Flow
**What:** The main Claude Code session runs the pipeline by spawning Task calls in sequence, reading intermediate JSON files, and passing context to the next stage.
**When to use:** Every trading cycle.
**Orchestration pseudo-flow:**
```
1. Generate cycle_id (timestamp-based)
2. Create state/cycles/{cycle_id}/ directory
3. Read state/strategy.md
4. Read 3 most recent cycle reports from state/reports/
5. Spawn Task: Scanner -> writes scanner_output.json
6. Read scanner_output.json, validate JSON structure
7. For each market (parallel Tasks): Spawn Task: Analyst -> writes analyst_{market_id}.json
8. Read all analyst outputs, merge into analyst_output.json
9. Spawn Task: Risk Manager -> reads portfolio + analyst output -> writes risk_output.json
10. Spawn Task: Planner -> reads all prior outputs + strategy -> writes trade_plan.json
11. Read trade_plan.json, execute trades via tools/execute_trade.py (main agent does this, not a sub-agent)
12. Write execution_results.json
13. Spawn Task: Reviewer -> reads all outputs + execution results -> writes reviewer_output.json + cycle report
14. Log total token cost
```

### Pattern 3: Analyst Bull/Bear Debate (D-05)
**What:** Single Analyst agent call that structures reasoning as Bull case, Bear case, then synthesis.
**When to use:** Every market analysis.
**Prompt pattern:**
```
Analyze market: "{question}"
Current price: {yes_price}

## Phase 1: Bull Case
Argue FOR this outcome being more likely than the market implies.
Find real-time evidence via web search supporting this position.

## Phase 2: Bear Case
Argue AGAINST this outcome. Find counter-evidence.
Identify risks, alternative scenarios, and reasons the market might be correct.

## Phase 3: Synthesis
Weighing both perspectives, estimate:
- true_probability: your best estimate (0.0-1.0)
- confidence: how confident you are in your estimate (0.0-1.0)
- reasoning: synthesis of Bull and Bear cases
```

### Pattern 4: Correlation Detection (Risk Manager - AGNT-06)
**What:** Risk Manager identifies correlated positions by analyzing market questions and categories.
**When to use:** When evaluating new positions against existing portfolio.
**Recommended approach:** Prompt-based semantic analysis within the Risk Manager agent.
```
For each proposed trade, check the existing portfolio:
1. Category match: Are markets in the same category/event group?
2. Question similarity: Do questions reference the same entity/outcome?
   - "Will X win election?" and "Will X be president?" are correlated
   - "Will Bitcoin hit 100k?" and "Will Bitcoin hit 80k?" are correlated
3. Outcome dependency: Would one resolving YES make the other more/less likely?

If correlation detected:
- Flag as correlated pair
- Reduce combined position sizing below single-position maximum
- Apply correlation_factor (0.5-0.7) to Kelly sizing for the second position
```

### Anti-Patterns to Avoid
- **Passing large data in Task prompt text:** Write to JSON files instead. Prompts have practical size limits and data gets lost on retry.
- **Using sub-agents for trade execution:** The main agent should execute trades directly (D-01: "Execute" is between Planner and Reviewer in the pipeline). Sub-agents should not have live trading capability.
- **Nesting sub-agents:** Sub-agents cannot spawn other sub-agents. The Analyst must do its Bull/Bear debate in a single call, not by spawning two sub-sub-agents.
- **Global state in agent prompts:** Each sub-agent gets a fresh context. Pass state via JSON files, not by assuming the agent remembers prior interactions.
- **Omitting `maxTurns`:** Without this, a confused sub-agent can run indefinitely, burning tokens. Always set in frontmatter.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Sub-agent spawning | Custom Python multi-process orchestrator | Claude Code Task tool with `.claude/agents/*.md` | Native infrastructure handles context isolation, tool restriction, model selection, and cost control |
| Agent output validation | Custom JSON schema validator in Python | Prompt engineering + simple structure checks in main agent | Sub-agent prompts enforce output format; main agent does basic structural validation |
| Market correlation detection | ML-based correlation engine | Prompt-based semantic analysis in Risk Manager agent | For prediction markets, category/question text analysis is sufficient; no need for numerical correlation |
| Cycle ID generation | UUID or database sequence | Timestamp-based string (`YYYYMMDD-HHMMSS`) | Human-readable, sortable, unique enough for non-concurrent cycles |
| Token cost tracking | Custom API call monitoring | Claude Code built-in usage reporting (available in `--output-format json` metadata) | The `cost` and `usage` fields in JSON output already track this |

## Common Pitfalls

### Pitfall 1: Sub-Agents Cannot Spawn Sub-Agents
**What goes wrong:** Attempting to have the Analyst spawn separate Bull and Bear sub-agents fails silently or errors.
**Why it happens:** Claude Code architectural constraint -- sub-agents don't have access to the Task/Agent tool.
**How to avoid:** Use a single Analyst call with structured prompting that forces both perspectives (D-05). The prompt must include explicit instructions for Bull case, Bear case, and Synthesis sections.
**Warning signs:** Agent definition includes `Task` in the `tools` list.

### Pitfall 2: JSON Output Reliability from Sub-Agents
**What goes wrong:** Sub-agents sometimes output prose instead of valid JSON, or include markdown code fences around JSON.
**Why it happens:** LLMs naturally produce conversational output; structured JSON requires explicit prompt engineering.
**How to avoid:**
- Be extremely explicit in the agent's system prompt about output format
- Instruct the agent to write JSON via the Write tool to a specific file path, not to output it conversationally
- Use the `Write` tool with exact file path in the prompt: "Write your output as valid JSON to `state/cycles/{cycle_id}/scanner_output.json`"
- The main agent should validate JSON structure after reading each file
**Warning signs:** Parsing errors when reading sub-agent output files.

### Pitfall 3: Analyst Parallel Task Failures
**What goes wrong:** One failed Analyst Task blocks or corrupts the entire analysis phase.
**Why it happens:** Network failures on web search, API rate limits, or individual market data issues.
**How to avoid:** Each Analyst Task is independent (D-08). Main agent should spawn all Tasks, collect results, and proceed with whatever succeeded. Missing analyst files for specific markets are acceptable -- just log and skip.
**Warning signs:** Cycle completes with 0 analyzed markets when Scanner found multiple candidates.

### Pitfall 4: Context Window Overflow
**What goes wrong:** Sub-agent runs out of context space before completing its task.
**Why it happens:** Reading too many large JSON files, or web search returning excessive content.
**How to avoid:**
- Scanner: Limit to MAX_MARKETS_PER_CYCLE (default 10)
- Analyst: One market per call
- Risk Manager: Pass only relevant portfolio positions, not full history
- Planner: Summarize prior outputs rather than passing raw data
- Set `maxTurns` to prevent runaway loops
**Warning signs:** Sub-agent output is truncated or missing expected fields.

### Pitfall 5: State Directory Not Created
**What goes wrong:** Sub-agent attempts to write to `state/cycles/{cycle_id}/` but the directory doesn't exist.
**Why it happens:** Main agent forgot to create the directory structure before spawning sub-agents.
**How to avoid:** Main agent must `mkdir -p state/cycles/{cycle_id}` and `mkdir -p state/reports` at cycle start, before any sub-agent is spawned.
**Warning signs:** Write tool errors about missing directories.

### Pitfall 6: Tool Path Issues in Sub-Agents
**What goes wrong:** Sub-agent's Bash command `python tools/discover_markets.py` fails with import errors.
**Why it happens:** Sub-agents may not have the same working directory assumptions as the main session.
**How to avoid:** Use absolute paths or ensure the working directory is explicit. Sub-agent prompts should reference the project root. The tool scripts already use `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` to resolve imports, but Python itself must be invoked correctly: `python tools/discover_markets.py` from the project root.
**Warning signs:** `ModuleNotFoundError` for `lib` package in sub-agent Bash output.

### Pitfall 7: maxTurns Too Low
**What goes wrong:** Sub-agent runs out of turns before completing its task and produces incomplete output.
**Why it happens:** Some agents need more turns than expected -- especially the Analyst (web search + Bull/Bear + synthesis) and Risk Manager (portfolio check + Kelly calculations for multiple positions).
**How to avoid:** Start with conservative limits and increase based on empirical testing. Recommended starting points:
- Scanner: 6 turns (discover + filter + write)
- Analyst: 12 turns (web search + analysis + write)
- Risk Manager: 10 turns (read files + portfolio + Kelly calculations + write)
- Planner: 8 turns (read all outputs + synthesize plan + write)
- Reviewer: 10 turns (read all + analyze + write report + write JSON)
**Warning signs:** Sub-agent output files are missing or contain partial data.

## Code Examples

### Sub-Agent YAML Frontmatter Configuration
```yaml
# Source: https://code.claude.com/docs/en/sub-agents
---
name: scanner
description: Scans Polymarket for tradable markets using instrument layer tools. Invoke at the start of each trading cycle.
tools: Bash, Read, Write
model: inherit
maxTurns: 6
permissionMode: bypassPermissions
---
```

### Task Tool Invocation (Main Agent Pattern)
The main Claude Code session spawns sub-agents like this:
```
# Claude internally calls the Task tool with:
# subagent_type: "scanner"
# prompt: "Discover markets for cycle {cycle_id}. Write output to state/cycles/{cycle_id}/scanner_output.json"
```

### JSON Schema: Scanner Output
```json
{
  "cycle_id": "20260326-143000",
  "timestamp": "2026-03-26T14:30:00Z",
  "markets_found": 7,
  "markets": [
    {
      "id": "market-abc-123",
      "condition_id": "0x1234...",
      "question": "Will Bitcoin exceed $100,000 by June 2026?",
      "yes_price": 0.65,
      "no_price": 0.35,
      "volume_24h": 50000,
      "liquidity": 25000,
      "category": "Crypto",
      "end_date": "2026-06-30T00:00:00Z",
      "yes_token_id": "token-yes-abc",
      "no_token_id": "token-no-abc",
      "neg_risk": false,
      "best_bid": 0.64,
      "best_ask": 0.66,
      "order_min_size": 5.0,
      "tick_size": 0.01
    }
  ]
}
```

### JSON Schema: Analyst Output (Per Market)
```json
{
  "cycle_id": "20260326-143000",
  "market_id": "market-abc-123",
  "question": "Will Bitcoin exceed $100,000 by June 2026?",
  "timestamp": "2026-03-26T14:32:15Z",
  "bull_case": {
    "argument": "Bitcoin ETF inflows accelerating, halving effect historically...",
    "evidence": ["source1", "source2"],
    "probability_estimate": 0.75
  },
  "bear_case": {
    "argument": "Regulatory headwinds, macro tightening...",
    "evidence": ["source3", "source4"],
    "probability_estimate": 0.55
  },
  "synthesis": {
    "estimated_probability": 0.68,
    "confidence": 0.72,
    "reasoning": "Bull case stronger due to ETF flows, but bear regulatory risk is real...",
    "market_price": 0.65,
    "edge": 0.03,
    "recommended_side": "YES",
    "sources_consulted": ["url1", "url2", "url3"]
  }
}
```

### JSON Schema: Risk Manager Output
```json
{
  "cycle_id": "20260326-143000",
  "timestamp": "2026-03-26T14:35:00Z",
  "portfolio_state": {
    "total_exposure": 85.50,
    "remaining_capacity": 114.50,
    "num_open_positions": 3,
    "utilization": 0.4275
  },
  "evaluated_markets": [
    {
      "market_id": "market-abc-123",
      "question": "Will Bitcoin exceed $100,000 by June 2026?",
      "estimated_prob": 0.68,
      "confidence": 0.72,
      "market_price": 0.65,
      "edge": 0.03,
      "kelly_raw": 0.048,
      "kelly_adjusted": 0.012,
      "recommended_side": "YES",
      "position_size_usdc": 12.50,
      "num_shares": 19.23,
      "approved": true,
      "correlation_flag": false,
      "sizing_notes": "Standard Kelly sizing, no correlation with existing positions"
    }
  ],
  "rejected_markets": [
    {
      "market_id": "market-xyz-456",
      "reason": "Edge below minimum threshold",
      "edge": 0.04,
      "min_threshold": 0.10
    }
  ],
  "risk_warnings": []
}
```

### JSON Schema: Trade Plan
```json
{
  "cycle_id": "20260326-143000",
  "timestamp": "2026-03-26T14:37:00Z",
  "strategy_context": "Conservative positioning, focus on high-confidence edges",
  "trades": [
    {
      "market_id": "market-abc-123",
      "question": "Will Bitcoin exceed $100,000 by June 2026?",
      "action": "BUY",
      "side": "YES",
      "token_id": "token-yes-abc",
      "size": 19.23,
      "price": 0.65,
      "cost_usdc": 12.50,
      "edge": 0.03,
      "estimated_prob": 0.68,
      "confidence": 0.72,
      "reasoning": "Strong ETF inflows support bullish case; 3% edge with 72% confidence",
      "neg_risk": false
    }
  ],
  "skipped_markets": [
    {
      "market_id": "market-xyz-456",
      "reason": "Insufficient edge (4% < 10% threshold)"
    }
  ]
}
```

### JSON Schema: Reviewer Output
```json
{
  "cycle_id": "20260326-143000",
  "timestamp": "2026-03-26T14:45:00Z",
  "summary": {
    "markets_scanned": 7,
    "markets_analyzed": 6,
    "trades_executed": 2,
    "trades_skipped": 4,
    "total_capital_deployed": 25.00,
    "cycle_pnl": 0.0
  },
  "trade_reviews": [
    {
      "market_id": "market-abc-123",
      "action_taken": "BUY YES",
      "size_usdc": 12.50,
      "edge": 0.03,
      "assessment": "Reasonable trade, edge exists but small. Monitor closely.",
      "improvement_suggestion": "Consider requiring higher minimum confidence for crypto markets"
    }
  ],
  "portfolio_after": {
    "total_exposure": 110.50,
    "num_positions": 5,
    "unrealized_pnl": -2.30
  },
  "learnings": [
    "Crypto market edges are thin -- may need higher confidence threshold",
    "Web search latency high for niche markets -- consider filtering earlier"
  ],
  "strategy_suggestions": [
    "Increase MIN_EDGE_THRESHOLD from 0.10 to 0.12 for crypto category",
    "Add end_date proximity as a market selection factor"
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Task tool (single name) | Agent tool (with Task as alias) | v2.1.63 (March 2026) | Wire name reverted to 'Task' in events; `Agent` name used in settings; both work as aliases |
| `subagent_type` required | `subagent_type` optional (defaults to general-purpose) | v2.1.63 | Simplifies agent definitions |
| No `maxTurns` in frontmatter | `maxTurns` supported | v2.1.x | Enables per-agent cost control |
| No persistent memory | `memory` field in frontmatter (user/project/local) | v2.1.x | Enables cross-session learning (useful for Phase 3 strategy evolution) |
| No background tasks | `background: true` in frontmatter | v2.1.x | Enables parallel background execution |

**Deprecated/outdated:**
- OpenAI GPT-4o for market analysis (replaced by Claude sub-agents per roadmap decision)
- `market_analyzer.py` (v1 module using OpenAI Responses API) -- replaced by Analyst sub-agent

## Open Questions

1. **Optimal `maxTurns` Values**
   - What we know: The frontmatter supports `maxTurns` field; too low truncates output, too high burns tokens
   - What's unclear: Exact turn counts needed per agent type (depends on web search latency, number of markets, portfolio complexity)
   - Recommendation: Start with recommended values (Scanner: 6, Analyst: 12, Risk Manager: 10, Planner: 8, Reviewer: 10) and adjust empirically during testing

2. **Token Cost Tracking Mechanism**
   - What we know: `--output-format json` includes `usage` metadata; Claude Code may surface cost info
   - What's unclear: Whether Task tool invocations report individual cost back to the parent, or only aggregate
   - Recommendation: Log `claude -p ... --output-format json | jq '.usage'` for each sub-agent call during testing to determine granularity. Alternatively, main agent can estimate from turn count.

3. **Parallel Analyst Task Behavior**
   - What we know: Claude Code can run up to 7 sub-agents simultaneously; Analyst calls per market are independent (D-08)
   - What's unclear: Whether the main Claude Code session can dispatch multiple Task tool calls truly in parallel, or if they execute sequentially
   - Recommendation: Test with 2-3 parallel Analyst Tasks first. The built-in sub-agent system supports parallel dispatch (the main session can invoke multiple Tasks). If parallel doesn't work, fall back to sequential with logging.

4. **Sub-Agent Working Directory**
   - What we know: Sub-agents inherit environment from the main conversation
   - What's unclear: Whether sub-agent Bash commands always execute from the project root
   - Recommendation: Use absolute paths in sub-agent prompts as a safety measure: `python /Users/aleksandrrazin/work/polymarket-agent/tools/discover_markets.py` -- or document the working directory assumption in each agent's prompt.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Claude Code CLI | Agent runtime | Yes | 2.1.50 | -- |
| Python 3.12 | Instrument tools | Yes | 3.12.9 | -- |
| pytest | Test suite | Yes | 9.0.2 | -- |
| `state/` directory | Inter-agent data | No (needs creation) | -- | Created during Phase 2 implementation |
| `.claude/agents/` | Sub-agent definitions | Exists (GSD agents present) | -- | New trading agents added alongside existing GSD agents |
| Phase 1 CLI tools | All sub-agents | Yes | All 7 tools present | -- |
| WebSearch/WebFetch | Analyst sub-agent | Yes (built-in Claude Code tools) | -- | -- |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- `state/` directory does not exist yet -- must be created as part of Phase 2 implementation (mkdir -p state/strategy.md state/reports/ state/cycles/)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | None (uses defaults) |
| Quick run command | `cd /Users/aleksandrrazin/work/polymarket-agent && python -m pytest tests/ -x -q` |
| Full suite command | `cd /Users/aleksandrrazin/work/polymarket-agent && python -m pytest tests/ -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| AGNT-01 | Main agent reads strategy.md and orchestrates pipeline | integration (manual) | Manual: run full cycle, verify output | -- Wave 0 |
| AGNT-02 | Scanner returns ranked market list | smoke | `python tools/discover_markets.py --pretty 2>/dev/null \| python -c "import json,sys; d=json.load(sys.stdin); assert isinstance(d,list)"` | -- (CLI test) |
| AGNT-03 | Analyst estimates probability with confidence | integration (manual) | Manual: spawn Analyst agent, verify JSON output | -- Wave 0 |
| AGNT-04 | Analyst includes Bull/Bear debate | integration (manual) | Manual: verify analyst output contains bull_case, bear_case, synthesis | -- Wave 0 |
| AGNT-05 | Risk Manager sizes positions via Kelly | unit | `python -m pytest tests/test_kelly.py -x -q` | Yes |
| AGNT-06 | Risk Manager detects correlated exposure | integration (manual) | Manual: create correlated positions, verify reduced sizing | -- Wave 0 |
| AGNT-07 | Planner creates trade plan | integration (manual) | Manual: verify trade_plan.json structure | -- Wave 0 |
| AGNT-08 | Reviewer writes cycle report | integration (manual) | Manual: verify report in state/reports/ | -- Wave 0 |
| AGNT-09 | Sub-agents return structured JSON | unit | `python -m pytest tests/test_agent_schemas.py -x -q` | -- Wave 0 |
| AGNT-10 | Sub-agents respect maxTurns | integration (manual) | Manual: verify agent terminates within limit | -- (frontmatter config) |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q` (quick run)
- **Per wave merge:** `python -m pytest tests/ -v` (full suite)
- **Phase gate:** Full suite green + manual cycle run before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_agent_schemas.py` -- JSON schema validation for all 5 sub-agent output formats (AGNT-09)
- [ ] `tests/test_cycle_state.py` -- Verify state directory creation, cycle ID generation, file write/read round-trip
- [ ] `state/` directory creation -- Needs to be created during implementation
- [ ] Sub-agent `.md` files -- All 5 need to be created in `.claude/agents/`

**Note:** Most Phase 2 requirements (AGNT-01 through AGNT-08, AGNT-10) are integration-level behaviors that involve Claude Code sub-agent execution. These cannot be tested in a traditional pytest unit test. The primary validation is a full cycle run. Unit tests cover the JSON schema contracts (AGNT-09) and state management mechanics.

## Sources

### Primary (HIGH confidence)
- [Claude Code Sub-agents Documentation](https://code.claude.com/docs/en/sub-agents) -- Complete reference for agent file format, YAML frontmatter fields, tool restrictions, maxTurns, permissionMode, memory, and all configuration options
- [Claude Code Headless/Programmatic Mode](https://code.claude.com/docs/en/headless) -- CLI flags for `-p`, `--output-format json`, `--json-schema`, `--max-turns`, and scripted execution

### Secondary (MEDIUM confidence)
- [Claude Code Agent Teams](https://code.claude.com/docs/en/agent-teams) -- Alternative multi-agent pattern (experimental, not recommended for this phase but documents parallel capabilities)
- [DEV.to: Task Tool Architecture](https://dev.to/bhaidar/the-task-tool-claude-codes-agent-orchestration-system-4bf2) -- Detailed analysis of Task tool parameters and spawning mechanics
- [ClaudeLog: Task/Agent Tools](https://claudelog.com/mechanics/task-agent-tools/) -- Community documentation of parallelization limits (up to 7 simultaneous agents)
- [Claude Code Changelog v2.1.41-2.1.63](https://www.vibesparking.com/en/blog/ai/claude/changelog/2026-03-04-claude-code-2141-2163-multi-agent-platform/) -- Version history including Agent/Task naming and subagent_type changes

### Tertiary (LOW confidence)
- [DEV.to: AI Trading Bot with Claude Code](https://dev.to/ji_ai/building-an-ai-trading-bot-with-claude-code-14-sessions-961-tool-calls-4o0n) -- Community experience building similar trading system (useful for pitfall identification but different architecture)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- Claude Code sub-agent system is well-documented; Phase 1 tools are already built and tested
- Architecture: HIGH -- Sequential pipeline pattern (D-01) is straightforward; JSON file passing (D-04) is standard; all design decisions are locked
- Pitfalls: HIGH -- Sub-agent constraints (no nesting, tool restrictions, maxTurns) are officially documented; JSON output reliability is a known LLM challenge
- JSON schemas: MEDIUM -- Schemas are designed based on Phase 1 tool outputs and requirements; exact fields may need adjustment during implementation

**Research date:** 2026-03-26
**Valid until:** 2026-04-10 (Claude Code evolving rapidly; sub-agent API relatively stable but check for new features)
