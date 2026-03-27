# Polymarket Autonomous Trading Agent

Paper trading is the default mode. NEVER switch to live trading without explicit user request.

## Quick Reference

- **Venv:** `source .venv/bin/activate` (required before any Python command)
- **Tools dir:** `tools/` — CLI scripts for market discovery, pricing, trading, portfolio
- **State dir:** `state/` — `strategy.md`, `core-principles.md`, `cycles/`, `reports/`
- **Config:** `config.py` loads from `.env` via python-dotenv
- **DB:** `trading.db` (SQLite, auto-created)
- **Sub-agents:** `.claude/agents/` — scanner, analyst, risk-manager, planner, reviewer, strategy-updater, position-monitor, outcome-analyzer
- **Detailed docs:** Root `CLAUDE.md` has architecture, file map, config params, key decisions, API details

---

## Trading Cycle Orchestration

When the user says "run a trading cycle" (or similar), execute this pipeline:

### Step 0: Initialization

1. Generate a cycle ID using current UTC timestamp: `YYYYMMDD-HHMMSS` format (e.g., `20260327-143000`).

2. Create directories:
   ```
   Bash: mkdir -p state/cycles/{cycle_id} state/reports
   ```

3. Read context files:
   - `state/strategy.md` — evolving trading strategy (may be minimal on first cycles)
   - `state/core-principles.md` — immutable human-set principles (read-only, never modify)
   - 3 most recent `state/reports/cycle-*.md` files (sorted descending by name). If none exist, note this is the inaugural cycle.

4. Log: "Starting trading cycle {cycle_id}"

5. **Extract core-principles constraints for sub-agents.** After reading `state/core-principles.md`, identify the constraints that are relevant to each downstream sub-agent (e.g., market focus categories for the scanner, position size caps for the risk manager, allowed trade types for the planner). When spawning any sub-agent in Steps 0.5 through 7, include the relevant core-principles constraints verbatim in that agent's prompt so it can respect operator rules. You decide what's relevant per agent — do not dump the entire file, just the applicable constraints.

### Step 0.5: Position Monitor

**Non-blocking** — if this step fails, log a warning and continue to Step 1.

Spawn the Position Monitor sub-agent:

```
Task(
  subagent_type="position-monitor",
  description="Monitor open positions",
  prompt="Review all open positions for trading cycle {cycle_id}. Check current prices, resolution status, and thesis validity. Write your output to state/cycles/{cycle_id}/position_monitor.json"
)
```

After completion:
- Read `state/cycles/{cycle_id}/position_monitor.json`
- Validate: `cycle_id`, `timestamp`, `positions_reviewed` (int), `recommendations` (array with `market_id`, `action`, `sell_size`, `reasoning`, `urgency`)
- If invalid or missing: log warning, continue to Step 1
- Log: "Position monitor reviewed {N} positions: {sell_count} SELL, {watch_count} WATCH, {hold_count} HOLD"

### Step 0.75: Execute Sells + Outcome Analysis

**Non-blocking** — if this step fails, log a warning and continue to Step 1.

**Execute sells** directly (no sub-agent) for each recommendation where `action == "SELL"`:

```bash
cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && python tools/sell_position.py \
  --market-id "{rec.market_id}" \
  --token-id "{rec.token_id}" \
  --side {rec.side} \
  --size {rec.sell_size} \
  --question "{rec.question}" \
  --reasoning "{rec.reasoning}" \
  --category "{rec.category}" \
  --pretty
```

After all sells, write `state/cycles/{cycle_id}/sell_results.json`:
```json
{
  "cycle_id": "{cycle_id}",
  "timestamp": "<ISO 8601 UTC>",
  "sells_attempted": 0,
  "sells_succeeded": 0,
  "sells_failed": 0,
  "results": []
}
```

Log: "Executed {N}/{M} sells successfully"

**Then spawn the Outcome Analyzer sub-agent:**

```
Task(
  subagent_type="outcome-analyzer",
  description="Analyze closed position outcomes",
  prompt="Analyze outcomes for all closed positions in trading cycle {cycle_id}. Calculate Brier scores, calibration metrics, and P&L by category. Write your output to state/cycles/{cycle_id}/outcome_analysis.json"
)
```

After completion:
- Read and validate `outcome_analysis.json` (must have `cycle_id`, `positions_analyzed`, `analyses` array, `calibration`, `summary`)
- If invalid: log warning, continue to Step 1
- Log: "Outcome analysis: {N} positions analyzed, avg Brier score: {score}"

### Step 1: Scanner

Spawn the Scanner sub-agent:

```
Task(
  subagent_type="scanner",
  description="Scan Polymarket markets",
  prompt="Discover active Polymarket markets for trading cycle {cycle_id}. Use --limit 20 to scan at least 20 markets. Write your output to state/cycles/{cycle_id}/scanner_output.json"
)
```

After completion:
- Read `state/cycles/{cycle_id}/scanner_output.json`
- Validate: `cycle_id`, `timestamp`, `markets_found` (number), `markets` (array)
- If missing/invalid/zero markets: log error, skip to Step 6 (Reviewer)
- Log: "Scanner found {N} candidate markets"

### Step 1b: Sweet-Spot Filtering

**You do this directly — no sub-agent.**

Filter the scanner's market list before sending to analysts:

1. **Price sweet spot:** Keep only markets where `yes_price` is between 0.15 and 0.85
2. **Existing positions:** Run `source .venv/bin/activate && python tools/get_portfolio.py --pretty` to check current portfolio. Skip markets where we already hold a position.
3. **WATCH markets:** If Step 0.5 produced position_monitor.json, also skip markets flagged as WATCH (weakening thesis — avoid doubling down).
4. **Rank** by `volume_24h` descending, take top 5-8 markets

If fewer than 3 pass, relax price range to 0.10-0.90 and retry.

Log: "Filtered {N} markets to {M} sweet-spot candidates for analysis"

### Step 2: Analysts (SEQUENTIAL — one at a time)

For each market in the filtered list, spawn an Analyst sub-agent **one at a time**:

```
Task(
  subagent_type="analyst",
  description="Analyze market {market.id}",
  prompt="Analyze this Polymarket market for trading cycle {cycle_id}:
Market ID: {market.id}
Question: {market.question}
Current YES price: {market.yes_price}
Current NO price: {market.no_price}
Category: {market.category}
End date: {market.end_date}
Volume 24h: {market.volume_24h}
Liquidity: {market.liquidity}
Write your output to state/cycles/{cycle_id}/analyst_{market.id}.json"
)
```

**IMPORTANT: Run analysts SEQUENTIALLY.** Spawn one, wait for completion, verify output file, then spawn the next. Do NOT spawn in parallel or in background — this causes session failures.

After all complete:
- Read and validate each `analyst_{market_id}.json` (must have `synthesis.estimated_probability`, `synthesis.confidence`, `synthesis.edge`, `synthesis.recommended_side`)
- Skip malformed outputs, continue with valid ones
- If zero valid: log warning, skip to Step 6
- Log: "Analyzed {N} markets successfully, {M} failed"

### Step 3: Risk Manager

```
Task(
  subagent_type="risk-manager",
  description="Evaluate risk for cycle",
  prompt="Evaluate risk and size positions for trading cycle {cycle_id}.
Read analyst outputs from: state/cycles/{cycle_id}/analyst_*.json
Valid analyst files: {list filenames}
Write your output to state/cycles/{cycle_id}/risk_output.json"
)
```

After completion:
- Read and validate `risk_output.json` (must have `portfolio_state`, `evaluated_markets` array, `rejected_markets` array)
- If invalid: log error, skip to Step 6
- Log: "Risk Manager approved {N} trades, rejected {M}"

### Step 4: Planner

```
Task(
  subagent_type="planner",
  description="Create trade plan",
  prompt="Create a trade plan for cycle {cycle_id}.
Read strategy from: state/strategy.md
Read scanner output from: state/cycles/{cycle_id}/scanner_output.json
Read analyst outputs from: state/cycles/{cycle_id}/analyst_*.json
Read risk assessment from: state/cycles/{cycle_id}/risk_output.json
Write your trade plan to state/cycles/{cycle_id}/trade_plan.json"
)
```

After completion:
- Read and validate `trade_plan.json` (must have `trades` array with `market_id`, `action`, `side`, `token_id`, `size`, `price`)
- If invalid: log error, skip to Step 6
- Log: "Trade plan has {N} trades to execute"

### Step 5: Execute Trades

**You execute trades directly — no sub-agent.**

For each trade in `trade_plan.trades`, run:

```bash
cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && python tools/execute_trade.py \
  --market-id "{trade.market_id}" \
  --token-id "{trade.token_id}" \
  --side {trade.side} \
  --size {trade.size} \
  --price {trade.price} \
  --question "{trade.question}" \
  --estimated-prob {trade.estimated_prob} \
  --edge {trade.edge} \
  --reasoning "{trade.reasoning}" \
  {--neg-risk if trade.neg_risk is true} \
  --category "{trade.category}" \
  --pretty
```

If a trade fails: log error, record as failed, continue with next trade.

After all trades, write `state/cycles/{cycle_id}/execution_results.json`:
```json
{
  "cycle_id": "{cycle_id}",
  "timestamp": "<ISO 8601 UTC>",
  "trades_attempted": 0,
  "trades_succeeded": 0,
  "trades_failed": 0,
  "results": []
}
```

Log: "Executed {N}/{M} trades successfully"

### Step 6: Reviewer

```
Task(
  subagent_type="reviewer",
  description="Review trading cycle",
  prompt="Review trading cycle {cycle_id}.
Read all cycle data from: state/cycles/{cycle_id}/
Files available: position_monitor.json, sell_results.json, outcome_analysis.json, scanner_output.json, analyst_*.json, risk_output.json, trade_plan.json, execution_results.json
Write your review to: state/cycles/{cycle_id}/reviewer_output.json
Write the cycle report to: state/reports/cycle-{cycle_id}.md"
)
```

After completion:
- Read and validate `reviewer_output.json` (must have `summary`, `learnings` array, `strategy_suggestions` array)
- Verify `state/reports/cycle-{cycle_id}.md` exists
- Log: "Cycle report written to state/reports/cycle-{cycle_id}.md"

### Step 7: Strategy Updater

```
Task(
  subagent_type="strategy-updater",
  description="Update trading strategy",
  prompt="Update the trading strategy based on cycle {cycle_id} review.
Read reviewer output from: state/cycles/{cycle_id}/reviewer_output.json
Read outcome analysis from: state/cycles/{cycle_id}/outcome_analysis.json
Read current strategy from: state/strategy.md
Write your update output to: state/cycles/{cycle_id}/strategy_update.json"
)
```

After completion:
- Read and validate `strategy_update.json` (must have `changes_applied`, `changes` array, `summary`)
- If fails: log error but do NOT fail the cycle — strategy update is post-cycle enhancement
- Log: "Strategy updated: {changes_applied} changes applied"

### Step 8: Completion

Log a summary:
```
Cycle {cycle_id} complete:
  Positions monitored: {N}
  Positions sold: {N}
  Outcome analyses: {N}
  Markets scanned: {N}
  Markets analyzed: {N}
  Trades executed: {N}
  Capital deployed: ${N} USDC
  Strategy changes: {N}
```

---

## Error Handling

| Failure | Action |
|---|---|
| Position Monitor fails | Log warning, continue to Step 1 (non-blocking) |
| Sell execution fails | Log error per sell, continue with remaining sells |
| Outcome Analyzer fails | Log warning, continue to Step 1 (non-blocking) |
| Scanner fails | STOP cycle, skip to Step 6 (Reviewer) |
| All analysts fail | Skip to Step 6 |
| Risk Manager fails | Skip to Step 6 |
| Planner fails | Skip to Step 6 |
| Single trade fails | Continue with remaining trades |
| Reviewer fails | Log error, cycle still complete |
| Strategy Updater fails | Log error, cycle still complete |

Always run the Reviewer even if earlier stages failed — every cycle produces a report.

---

## Critical Rules

### Sub-Agent Spawning
- **ALWAYS** use the `Task` tool with `subagent_type` to spawn sub-agents
- **NEVER** use `Bash("claude ...")` or `Bash("claude --agent ...")` to spawn sub-agents — this causes nested session failures
- Run analysts **sequentially** (one Task call at a time, wait for completion)
- Other sub-agents (scanner, risk-manager, planner, reviewer, strategy-updater) are each spawned once

### Safety
- **NEVER** modify `.env`, `trading.db`, or `config.py`
- **NEVER** modify `state/core-principles.md` — human-operated only
- **NEVER** set `PAPER_TRADING=false` or use `--live` without explicit user instruction
- `state/strategy.md` is modified ONLY by the Strategy Updater sub-agent (Step 7)

### File Discipline
- Cycle outputs go to `state/cycles/{cycle_id}/`
- Cycle reports go to `state/reports/cycle-{cycle_id}.md`
- Keep all intermediate JSON files for audit trail
