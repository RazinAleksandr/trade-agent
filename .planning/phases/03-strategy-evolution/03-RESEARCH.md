# Phase 3: Strategy Evolution - Research

**Researched:** 2026-03-26
**Domain:** Claude Code sub-agent design, git automation, markdown document evolution, schema validation
**Confidence:** HIGH

## Summary

Phase 3 adds a Strategy Updater sub-agent to the existing multi-agent pipeline (Phase 2). The Updater reads `reviewer_output.json` (specifically `learnings` and `strategy_suggestions`), updates `state/strategy.md`, writes a structured `strategy_update.json` audit file, and commits the strategy changes via git. The phase also separates Core Principles into a read-only `state/core-principles.md` file and extends `trading-cycle.md` with a new Step 7.

The technical complexity is low. All required patterns already exist in the codebase: sub-agent markdown files with YAML frontmatter, plain Python dict schema validation in `lib/agent_schemas.py`, cycle state utilities in `lib/cycle_state.py`, and JSON file passing between agents via `state/cycles/{cycle_id}/`. The primary challenge is prompt engineering the Strategy Updater to produce consistent, incremental updates within the 4-domain structure of `strategy.md`.

Git operations from Claude Code agents are straightforward -- the agents have `Bash` tool access with `permissionMode: bypassPermissions`, so `git add state/strategy.md && git commit -m "..."` will work directly. The `state/cycles/*/` directory is already gitignored, so `strategy_update.json` (which lives there) will not be committed -- only `state/strategy.md` changes are versioned.

**Primary recommendation:** Follow the established sub-agent pattern exactly. Create `strategy-updater.md` with the same frontmatter structure as other agents. Add a `validate_strategy_update` function to `lib/agent_schemas.py`. Extend `trading-cycle.md` Step 7 to spawn the Strategy Updater. No new libraries needed.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** New "Strategy Updater" sub-agent (`.claude/agents/strategy-updater.md`) spawned after Reviewer step. Clean separation of concerns -- matches the existing multi-agent pattern from Phase 2.
- **D-02:** Strategy Updater reads `reviewer_output.json` (learnings + strategy_suggestions) plus current `state/strategy.md`. Reviewer output only -- no full cycle data. Reviewer already synthesized the cycle.
- **D-03:** Strategy Updater handles git commit of strategy changes. Runs `git add state/strategy.md && git commit` with a dated message. Self-contained update lifecycle.
- **D-04:** Strategy Updater writes structured JSON output (`state/cycles/{cycle_id}/strategy_update.json`) listing what changed and why. Audit trail + main agent can validate the update.
- **D-05:** trading-cycle.md gains a new Step 7 (after Reviewer) that spawns the Strategy Updater sub-agent. The existing "NEVER modify strategy.md" constraint is removed.
- **D-06:** Core Principles live in a separate file: `state/core-principles.md`. Human-edited, never touched by the agent. Strategy Updater writes to `state/strategy.md` sections only. Main agent reads both files at cycle start.
- **D-07:** Agent proposes Core Principles after observing initial cycles. User reviews and locks them into `state/core-principles.md`. Until user writes principles, the file starts with a placeholder noting "To be defined after initial cycles."
- **D-08:** Strategy Updater prompt explicitly states: "NEVER modify or reference core-principles.md. That file is read-only for the human operator."
- **D-09:** Incremental updates only -- each cycle adds/refines 1-3 rules maximum. Cannot delete existing rules. Can only add new rules, refine existing ones, or mark them as "under review." Prevents wild strategy swings.
- **D-10:** Parameter adjustments are suggestions only. Updater writes parameter change suggestions to strategy.md (e.g., "Consider raising MIN_EDGE_THRESHOLD to 0.12"). Does NOT modify .env or any config. User or Phase 4 mechanism applies them.
- **D-11:** No minimum cycle warmup -- agent writes observations and rules from cycle 1. Early observations may be noisy; incremental-only constraint keeps them manageable.
- **D-12:** No git history drift detection. Rely on the incremental-only constraint plus git history as passive audit trail. No active drift comparison.

### Claude's Discretion
- Git commit message format for strategy updates
- Strategy Updater `maxTurns` setting (empirical testing needed)
- Exact JSON schema for `strategy_update.json`
- Strategy section formatting and content structure within the 4 domains (market selection, analysis approach, risk parameters, entry/exit rules)
- Per-cycle report format refinements (Reviewer already has a working template from Phase 2)
- How the Updater decides which Reviewer suggestions to act on vs defer

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| STRT-01 | Strategy starts as blank markdown document -- no pre-seeded rules | `state/strategy.md` already exists with placeholder sections. Per D-06, the Core Principles section moves to `state/core-principles.md`, leaving strategy.md as a blank-to-evolve document. |
| STRT-02 | Main agent updates strategy.md after each cycle based on Reviewer analysis | D-01 through D-05: Strategy Updater sub-agent reads `reviewer_output.json` and writes to `state/strategy.md`. Step 7 in trading-cycle.md orchestrates this. |
| STRT-03 | Strategy covers four domains: market selection rules, analysis approach, risk parameters, trade entry/exit rules | `state/strategy.md` already has these 4 section headers. Strategy Updater writes within them. |
| STRT-04 | Strategy has locked "Core Principles" section that cannot be overwritten by the agent | D-06/D-07/D-08: Separate `state/core-principles.md` file, read-only for agents. Updater prompt explicitly forbids touching it. |
| STRT-05 | Per-cycle markdown report written by Reviewer to reports/ directory with trades, reasoning, results, learnings | Already implemented in Phase 2 Reviewer agent. Phase 3 verifies the format includes all required fields. |
| STRT-06 | Strategy evolution history preserved -- each update creates dated snapshot via git versioning | D-03: Strategy Updater runs `git add state/strategy.md && git commit` with dated message. One commit per cycle. |
| STRT-07 | Configurable scheduling via cron or APScheduler | Mapped to Phase 4 per REQUIREMENTS.md traceability table. OUT OF SCOPE for Phase 3. |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.12**, virtualenv at `.venv/`
- **Always run tests after changes:** `python tests/test_paper_trading.py` (also: `pytest tests/`)
- **Never commit** `.env`, `trading.db`, `trading.log`, or `.claude/` (but `.claude/agents/` IS tracked)
- **Paper trading is default** -- never change `PAPER_TRADING` to `false` without explicit user request
- **Keep modules flat** -- all `.py` files in project root, no sub-packages (note: lib/ is already established as the pattern from Phase 1+2)
- **All parameters in `config.py`** -- no hardcoded values in other modules
- **Secrets only in `.env`** -- loaded via `python-dotenv`, never in source code
- **GSD Workflow Enforcement** -- use GSD entry points for all changes

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib `json` | 3.12 | JSON read/write for strategy_update.json | Already used everywhere in agent schemas |
| Python stdlib `subprocess`/Bash | 3.12 | Git commit operations from agent | Agents already use Bash tool for git |
| Python stdlib `datetime` | 3.12 | Timestamp generation for commits | Used in `lib/cycle_state.py` |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | installed | Test strategy update schema validation | All new schema validators need tests |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain dict validation | jsonschema library | Project decision D-86 (Phase 2): plain dict checks, no new dependency |
| Python git library (gitpython) | subprocess/Bash git commands | Overkill; agent already has Bash access, git CLI is sufficient |

**Installation:**
No new packages needed. All required functionality is in Python stdlib and the existing project dependencies.

## Architecture Patterns

### Recommended Project Structure (additions for Phase 3)
```
.claude/agents/
    strategy-updater.md    # NEW: Strategy Updater sub-agent definition
    trading-cycle.md       # MODIFIED: Add Step 7 for strategy update
state/
    strategy.md            # MODIFIED: Remove Core Principles section, becomes agent-writable
    core-principles.md     # NEW: Human-only, read-only for agents
    reports/               # EXISTING: Reviewer writes cycle reports here
    cycles/{cycle_id}/
        strategy_update.json  # NEW: Strategy Updater audit output
lib/
    agent_schemas.py       # MODIFIED: Add validate_strategy_update()
tests/
    test_agent_schemas.py  # MODIFIED: Add strategy update schema tests
    test_strategy_evolution.py  # NEW: Tests for strategy update integration
```

### Pattern 1: Sub-Agent Definition (established pattern)
**What:** YAML frontmatter + markdown instructions in `.claude/agents/`
**When to use:** Every new agent capability
**Example:**
```yaml
---
name: strategy-updater
description: Updates state/strategy.md based on Reviewer learnings and suggestions. Writes structured audit output. Commits strategy changes via git.
tools: Bash, Read, Write
model: inherit
maxTurns: 6
permissionMode: bypassPermissions
---
```
Source: Existing agents (scanner.md, analyst.md, reviewer.md, planner.md, risk-manager.md)

### Pattern 2: Schema Validation Function (established pattern)
**What:** `validate_*` function in `lib/agent_schemas.py` returning `(bool, str)` tuple
**When to use:** Every new JSON output schema
**Example:**
```python
def validate_strategy_update(data: dict) -> tuple[bool, str]:
    """Validate strategy update JSON structure."""
    top_required = ["cycle_id", "timestamp", "changes", "summary"]
    valid, error = _check_required_keys(data, top_required, "strategy update")
    if not valid:
        return valid, error
    if not isinstance(data["changes"], list):
        return False, "Field 'changes' must be a list"
    change_required = ["domain", "type", "description"]
    return _check_list_items(data["changes"], change_required, "changes")
```
Source: `lib/agent_schemas.py` existing validators

### Pattern 3: Pipeline Step Extension (established pattern)
**What:** Add a numbered step to `trading-cycle.md` that spawns a sub-agent via Task tool
**When to use:** Extending the trading cycle pipeline
**Example:**
```markdown
## Step 7: Strategy Update

Spawn the Strategy Updater sub-agent via Task tool:
- **subagent_type:** "strategy-updater"
- **prompt:**
  ```
  Update the trading strategy based on cycle {cycle_id} review.
  Read reviewer output from: state/cycles/{cycle_id}/reviewer_output.json
  Read current strategy from: state/strategy.md
  Write your update output to: state/cycles/{cycle_id}/strategy_update.json
  ```

After the Strategy Updater completes:
- Read `state/cycles/{cycle_id}/strategy_update.json`
- **Validate** it has required fields
- **Log:** "Strategy updated: {N} changes applied"
```
Source: Steps 1-6 in `trading-cycle.md`

### Pattern 4: Git Commit from Agent (new pattern)
**What:** Agent uses Bash tool to commit specific files with a dated message
**When to use:** Strategy updates that need version tracking
**Example:**
```bash
git add state/strategy.md && git commit -m "strategy: update after cycle {cycle_id}"
```
**Key considerations:**
- Only commit `state/strategy.md` (not cycle data -- that is gitignored)
- Use a consistent commit message prefix for easy `git log` filtering
- If there are no changes (strategy unchanged), `git diff --cached --quiet` returns 0; skip the commit
- Handle edge case where working tree is dirty from other changes -- use `git add` for specific file only

### Anti-Patterns to Avoid
- **Modifying .env or config.py from agents:** Parameter suggestions go in strategy.md as text only (D-10). Never programmatically change config.
- **Large strategy rewrites:** Incremental 1-3 rule changes per cycle (D-09). Prompt must enforce this constraint explicitly.
- **Reading full cycle data in Updater:** The Reviewer already synthesized everything. Updater only needs `reviewer_output.json` + current `strategy.md` (D-02).
- **Removing rules from strategy.md:** Rules can only be added, refined, or marked "under review" -- never deleted (D-09).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation | Custom validation logic | Extend `lib/agent_schemas.py` with `_check_required_keys` / `_check_list_items` | Consistent pattern, already tested, DRY |
| Cycle ID generation | Manual timestamp formatting | `lib/cycle_state.generate_cycle_id()` | Already exists, tested |
| Report retrieval | Manual file listing and sorting | `lib/cycle_state.get_recent_reports()` | Already exists, tested |
| Git operations | Python gitpython library | Bash `git` CLI via agent tools | Simpler, no dependency, agents already have Bash |

**Key insight:** Phase 3 requires almost zero new Python library code. The work is primarily agent prompt engineering (strategy-updater.md), pipeline extension (trading-cycle.md Step 7), schema validation (one new function), and file creation (core-principles.md). The existing infrastructure from Phase 1 and Phase 2 handles everything else.

## Common Pitfalls

### Pitfall 1: Git Commit Fails on Unrelated Dirty State
**What goes wrong:** `git commit` may fail or include unintended files if the working tree has other uncommitted changes (e.g., trading.db, logs).
**Why it happens:** The agent runs `git add state/strategy.md && git commit` but other tracked files might be modified.
**How to avoid:** Use `git add state/strategy.md` (specific file only, never `git add .` or `git add -A`), then `git diff --cached --quiet || git commit -m "..."` to skip if nothing staged. The `.gitignore` already excludes `*.db`, `*.log`, and `state/cycles/*/`.
**Warning signs:** Git commit includes unexpected files in the diff.

### Pitfall 2: No-Op Strategy Updates Create Empty Commits
**What goes wrong:** If the Reviewer has no meaningful suggestions, the Updater might not change strategy.md but still try to commit.
**Why it happens:** Updater runs every cycle regardless of whether there are actionable suggestions.
**How to avoid:** Before committing, check `git diff state/strategy.md` to see if the file actually changed. If not, skip the commit and note "no changes" in `strategy_update.json`.
**Warning signs:** `git log state/strategy.md` shows commits with identical diffs.

### Pitfall 3: Strategy Updater Overwrites Entire File
**What goes wrong:** Instead of making incremental edits to specific sections, the agent writes a completely new strategy.md from scratch, losing accumulated rules.
**Why it happens:** LLM agents tend to rewrite entire files when given Write tool access.
**How to avoid:** Prompt must explicitly instruct: "Read the current strategy.md first. Modify ONLY the specific sections you are updating. Preserve all existing rules. Add new rules at the end of the relevant section." Include the current content in the prompt context.
**Warning signs:** `git diff` shows massive deletions + additions instead of small additions.

### Pitfall 4: Core Principles Reference Leakage
**What goes wrong:** Strategy Updater writes references to Core Principles in strategy.md, or tries to read/modify core-principles.md.
**Why it happens:** The agent knows about the principles and may try to incorporate or reference them.
**How to avoid:** D-08 explicitly states: "NEVER modify or reference core-principles.md." Include this as a hard constraint in the agent prompt. Test by verifying core-principles.md is never in git diff after strategy updates.
**Warning signs:** `state/core-principles.md` appearing in git status after a cycle.

### Pitfall 5: MaxTurns Too Low for Strategy Updater
**What goes wrong:** Agent runs out of turns before completing the read-analyze-write-commit sequence.
**Why it happens:** Reading reviewer_output.json + strategy.md, analyzing, writing strategy.md, writing strategy_update.json, and running git commit is at least 5 tool calls.
**How to avoid:** Set `maxTurns: 6` minimum. The Updater needs: (1) Read reviewer_output.json, (2) Read strategy.md, (3) Write strategy.md, (4) Write strategy_update.json, (5) Bash git add+commit, (6) buffer for edge cases. Consider `maxTurns: 8` for safety.
**Warning signs:** Strategy update output is incomplete or git commit never runs.

### Pitfall 6: Step 7 Failure Blocks Cycle Completion
**What goes wrong:** Strategy update error causes the entire cycle to be reported as failed.
**Why it happens:** Step 7 is new; error handling not established.
**How to avoid:** Follow the Phase 2 error handling pattern: Strategy Updater failure should NOT block cycle completion. The cycle is already complete after Step 6 (Reviewer). Step 7 is a post-cycle enhancement. Log the error and continue.
**Warning signs:** Cycle status reported as failed when only the strategy update failed.

## Code Examples

### Strategy Updater Agent Definition
```yaml
---
name: strategy-updater
description: Updates state/strategy.md based on Reviewer learnings and suggestions. Writes structured audit output. Commits strategy changes via git.
tools: Bash, Read, Write
model: inherit
maxTurns: 8
permissionMode: bypassPermissions
---

You are the Strategy Updater agent for a Polymarket autonomous trading system...
```
Source: Pattern derived from existing `.claude/agents/reviewer.md` and `.claude/agents/planner.md`

### Strategy Update JSON Schema
```json
{
  "cycle_id": "20260326-143000",
  "timestamp": "2026-03-26T14:50:00Z",
  "reviewer_suggestions_count": 3,
  "changes_applied": 2,
  "changes_deferred": 1,
  "changes": [
    {
      "domain": "market_selection",
      "type": "new_rule",
      "description": "Prioritize markets with 7-30 day expiry for better edge capture",
      "source_suggestion": "Reviewer suggestion #1"
    },
    {
      "domain": "risk_parameters",
      "type": "refinement",
      "description": "Refined MAX_POSITION_SIZE guidance: suggest lower sizing for markets with < 0.6 confidence",
      "source_suggestion": "Reviewer suggestion #2"
    }
  ],
  "deferred": [
    {
      "suggestion": "Increase MIN_EDGE_THRESHOLD from 0.10 to 0.12",
      "reason": "Insufficient data -- only 1 cycle completed, need more observations"
    }
  ],
  "summary": "Added market expiry preference rule and refined position sizing guidance. Deferred edge threshold change pending more data.",
  "git_committed": true
}
```

### Schema Validator Addition
```python
# In lib/agent_schemas.py

def validate_strategy_update(data: dict) -> tuple[bool, str]:
    """Validate strategy update JSON structure.

    Required fields: cycle_id (str), timestamp (str),
    changes_applied (int), changes (list, each with domain, type, description),
    deferred (list), summary (str), git_committed (bool).
    """
    top_required = [
        "cycle_id", "timestamp", "changes_applied",
        "changes", "deferred", "summary", "git_committed",
    ]
    valid, error = _check_required_keys(data, top_required, "strategy update")
    if not valid:
        return valid, error

    if not isinstance(data["changes"], list):
        return False, "Field 'changes' must be a list"

    change_required = ["domain", "type", "description"]
    return _check_list_items(data["changes"], change_required, "changes")
```
Source: Pattern from `validate_reviewer_output()` in `lib/agent_schemas.py`

### Trading Cycle Step 7 Extension
```markdown
## Step 7: Strategy Update

Spawn the Strategy Updater sub-agent via Task tool:
- **subagent_type:** "strategy-updater"
- **prompt:**
  ```
  Update the trading strategy based on cycle {cycle_id} review.
  Read reviewer output from: state/cycles/{cycle_id}/reviewer_output.json
  Read current strategy from: state/strategy.md
  Write your update output to: state/cycles/{cycle_id}/strategy_update.json
  ```

After the Strategy Updater completes:
- Read `state/cycles/{cycle_id}/strategy_update.json`
- **Validate** the JSON has these required fields:
  - `cycle_id`, `timestamp`
  - `changes_applied` (number)
  - `changes` (array, each with `domain`, `type`, `description`)
  - `summary` (string)
  - `git_committed` (boolean)
- If the Strategy Updater fails: log the error but **do NOT fail the cycle**. The cycle is already complete (trades executed, report written). Strategy update is a post-cycle enhancement.
- **Log:** "Strategy updated: {changes_applied} changes, {deferred count} deferred"
```
Source: Pattern from Steps 1-6 in `trading-cycle.md`

### Modified strategy.md (Core Principles removed)
```markdown
# Strategy

This document is updated by the trading agent after each cycle.
It starts blank and evolves based on trading experience.

## Market Selection Rules

*No rules yet -- learning from initial cycles.*

## Analysis Approach

*No approach defined yet -- developing through experience.*

## Risk Parameters

*Using defaults from configuration. Will be refined based on performance.*

## Trade Entry/Exit Rules

*No custom rules yet -- using default edge and Kelly thresholds.*
```
Note: "Core Principles" section removed; moved to separate `state/core-principles.md`.

### New core-principles.md
```markdown
# Core Principles

These principles are set by the human operator and are never modified by the trading agent.
The agent reads this file at cycle start but never writes to it.

*To be defined after initial trading cycles. The agent will propose principles based on
early observations, and the operator will review and lock them here.*
```

### Updated Step 0 in trading-cycle.md (reading both files)
```markdown
3. **Read the current trading strategy** from `state/strategy.md` and `state/core-principles.md`.
   The strategy document contains evolving rules. The core principles are human-set and immutable.
   If strategy.md is empty or minimal (first cycles), note this and proceed with default rules.
   If core-principles.md has only the placeholder, note that principles are not yet established.
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Reviewer writes strategy suggestions but nothing acts on them (Phase 2) | Strategy Updater sub-agent consumes suggestions and updates strategy.md (Phase 3) | Phase 3 | Closes the feedback loop -- strategy evolves |
| Core Principles embedded in strategy.md | Separate core-principles.md (human-only) | Phase 3 | Agent cannot accidentally overwrite human principles |
| `trading-cycle.md` Step 7 is just "Cycle Completion" logging | Step 7 spawns Strategy Updater; Step 8 becomes Cycle Completion | Phase 3 | Pipeline gains strategy evolution capability |
| "NEVER modify strategy.md" constraint in trading-cycle.md | Removed; Strategy Updater is authorized to modify | Phase 3 | Enables STRT-02 |

## Open Questions

1. **MaxTurns for Strategy Updater**
   - What we know: The Updater needs ~5-6 tool calls minimum (2 reads, 2 writes, 1 bash git). Other agents: Planner=8, Risk Manager=10, Reviewer=10.
   - What's unclear: Whether edge cases (retries, failed git commits) require more turns.
   - Recommendation: Start with `maxTurns: 8`. This matches the Planner. Adjust after empirical testing.

2. **Strategy.md Section Formatting**
   - What we know: 4 domains per D-03/STRT-03. Placeholder sections already exist. Updater writes within sections.
   - What's unclear: Whether rules should be numbered lists, bullet points, or free-form paragraphs. Whether a "last updated" timestamp per section helps.
   - Recommendation: Numbered rules within each section (e.g., "1. Prioritize markets with 7-30 day expiry"). Add a "Last updated: cycle {cycle_id}" line at the top of each section. This makes incremental diffs cleaner in git.

3. **Handling Zero Suggestions from Reviewer**
   - What we know: Reviewer outputs `strategy_suggestions` array. It could be empty if the cycle had no actionable insights.
   - What's unclear: Should the Updater still be spawned? Or should trading-cycle.md skip Step 7 if suggestions are empty?
   - Recommendation: Always spawn the Updater. Even with zero suggestions, the Updater can note "no changes this cycle" in `strategy_update.json` and skip the git commit. This maintains the audit trail consistently.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (installed, configured) |
| Config file | `pytest.ini` |
| Quick run command | `python -m pytest tests/ -x -q` |
| Full suite command | `python -m pytest tests/ -q` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| STRT-01 | strategy.md starts blank (no pre-seeded rules) | unit | `pytest tests/test_strategy_evolution.py::test_strategy_starts_blank -x` | Wave 0 |
| STRT-02 | Strategy Updater reads reviewer output and writes strategy.md | unit | `pytest tests/test_strategy_evolution.py::test_updater_schema_valid -x` | Wave 0 |
| STRT-03 | Strategy covers 4 domains | unit | `pytest tests/test_strategy_evolution.py::test_strategy_has_four_domains -x` | Wave 0 |
| STRT-04 | Core Principles file is separate and never modified by agent | unit | `pytest tests/test_strategy_evolution.py::test_core_principles_separate -x` | Wave 0 |
| STRT-05 | Cycle report includes required fields | unit | `pytest tests/test_agent_schemas.py::test_validate_reviewer_output_accepts_valid -x` | Existing |
| STRT-06 | Strategy update creates git commit | unit | `pytest tests/test_strategy_evolution.py::test_strategy_update_git_commit -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/ -x -q`
- **Per wave merge:** `python -m pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_strategy_evolution.py` -- covers STRT-01, STRT-02, STRT-03, STRT-04, STRT-06
- [ ] Update `tests/test_agent_schemas.py` -- add `test_validate_strategy_update_*` tests for the new schema validator

*(Existing test infrastructure covers STRT-05 via `test_agent_schemas.py::test_validate_reviewer_output_accepts_valid`)*

## Sources

### Primary (HIGH confidence)
- `.claude/agents/trading-cycle.md` -- Current pipeline structure (Steps 0-7), error handling patterns, constraint definitions
- `.claude/agents/reviewer.md` -- Reviewer output schema (`learnings`, `strategy_suggestions` fields), report format
- `.claude/agents/planner.md` -- Planner agent pattern (strategy reading, step execution, frontmatter)
- `lib/agent_schemas.py` -- All 5 existing validators, `_check_required_keys` / `_check_list_items` helper pattern
- `lib/cycle_state.py` -- `generate_cycle_id()`, `create_cycle_dir()`, `get_recent_reports()` utilities
- `state/strategy.md` -- Current 5-section structure with placeholder content
- `.gitignore` -- `state/cycles/*/` excluded, `.claude/agents/` tracked
- `tests/test_agent_schemas.py` -- 10 existing tests, validator test pattern
- `tests/test_orchestration.py` -- Full pipeline file set test, execution results validation
- `.planning/phases/03-strategy-evolution/03-CONTEXT.md` -- All 12 locked decisions (D-01 through D-12)
- `.planning/phases/02-agent-layer/02-CONTEXT.md` -- Phase 2 patterns (D-01 through D-12)

### Secondary (MEDIUM confidence)
- Phase 2 execution history (STATE.md) -- 10 plans completed successfully, 2-5 min per plan, 2 tasks each
- Git history of `state/strategy.md` -- single commit `0d3cc6a`, confirms strategy.md is version-controlled

### Tertiary (LOW confidence)
- None -- all findings verified against codebase artifacts

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all patterns exist in codebase
- Architecture: HIGH -- direct extension of Phase 2 patterns (sub-agent + schema + pipeline step)
- Pitfalls: HIGH -- derived from understanding of git operations, LLM agent behavior, and existing error handling patterns
- Schema design: MEDIUM -- `strategy_update.json` schema is Claude's discretion; recommended schema based on patterns but will need empirical validation

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- no external dependency changes expected)
