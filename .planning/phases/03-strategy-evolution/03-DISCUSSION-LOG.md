# Phase 3: Strategy Evolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-26
**Phase:** 03-strategy-evolution
**Areas discussed:** Strategy update mechanism, Core Principles protection, Evolution guardrails

---

## Strategy Update Mechanism

### Q1: Who should update strategy.md after each cycle?

| Option | Description | Selected |
|--------|-------------|----------|
| New sub-agent | Dedicated 'Strategy Updater' sub-agent spawned after Reviewer. Reads Reviewer output + current strategy, writes updated strategy. Clean separation of concerns. | ✓ |
| Main agent inline | Extend trading-cycle.md with a new Step 7 where the main agent updates strategy.md itself. Simpler but adds complexity to 50-turn agent. | |
| Post-cycle script | Python tool in tools/ that programmatically merges Reviewer suggestions into strategy.md. Less flexible but deterministic. | |

**User's choice:** New sub-agent (Recommended)
**Notes:** None

### Q2: What inputs should the Strategy Updater sub-agent use?

| Option | Description | Selected |
|--------|-------------|----------|
| Reviewer output only | Reads reviewer_output.json (learnings + strategy_suggestions) + current strategy.md. Focused, minimal context. | ✓ |
| Full cycle data | Reads all cycle files. Richer context but much more token-heavy. | |
| Reviewer + last 3 reports | Reviewer output plus recent cycle reports for pattern detection. Moderate token cost. | |

**User's choice:** Reviewer output only (Recommended)
**Notes:** None

### Q3: Should the Strategy Updater also handle git commit of strategy changes?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, updater commits | Updater writes strategy.md then runs git add + commit. Self-contained update lifecycle. | ✓ |
| No, main agent commits | Updater only writes the file. Main agent handles git commit after validation. | |

**User's choice:** Yes, updater commits (Recommended)
**Notes:** None

### Q4: Should the Strategy Updater also produce structured JSON output?

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, write changes log | Write strategy_update.json to state/cycles/{cycle_id}/ listing what changed and why. | ✓ |
| No, just update the file | strategy.md is the only output. Simpler but no structured record. | |

**User's choice:** Yes, write changes log (Recommended)
**Notes:** None

---

## Core Principles Protection

### Q1: How should the locked Core Principles section be protected?

| Option | Description | Selected |
|--------|-------------|----------|
| Separate file + compose | Core Principles in state/core-principles.md (human-edited). Strategy Updater writes strategy.md sections only. Main agent reads both. | ✓ |
| Read-back validation | Updater writes full file, main agent validates Core Principles unchanged via checksum. | |
| Template injection | Updater receives Core Principles as read-only input, must include verbatim. Prompt-enforced. | |

**User's choice:** Separate file + compose (Recommended)
**Notes:** None

### Q2: Who defines the initial Core Principles content?

| Option | Description | Selected |
|--------|-------------|----------|
| User writes them | User writes core-principles.md with trading philosophy and non-negotiable rules. | |
| Start empty, user fills later | core-principles.md starts blank. User adds principles after observing cycles. | |
| Agent proposes, user approves | After initial cycles, agent proposes core principles. User reviews and locks into core-principles.md. | ✓ |

**User's choice:** Agent proposes, user approves
**Notes:** None

---

## Evolution Guardrails

### Q1: How aggressively should the Strategy Updater modify strategy.md each cycle?

| Option | Description | Selected |
|--------|-------------|----------|
| Incremental only | Each cycle adds/refines 1-3 rules max. Cannot delete existing rules — only add, refine, or mark "under review." | ✓ |
| Full rewrites allowed | Agent can rewrite any section freely. More adaptive but risks losing learnings. | |
| Append-only log | Chronological log of observations. Never edits previous entries. Simple but unwieldy. | |

**User's choice:** Incremental only (Recommended)
**Notes:** None

### Q2: Should the Strategy Updater be able to adjust configurable trading parameters?

| Option | Description | Selected |
|--------|-------------|----------|
| Suggest only | Writes parameter change suggestions to strategy.md. Does NOT modify .env. User applies them. | ✓ |
| Auto-adjust within bounds | Modify parameters in .env within pre-set bounds. More autonomous but riskier. | |
| No parameter changes | Strategy is qualitative rules only. Parameters stay fixed until user changes them. | |

**User's choice:** Suggest only (Recommended)
**Notes:** None

### Q3: Should there be a minimum number of cycles before writing strategy rules?

| Option | Description | Selected |
|--------|-------------|----------|
| No minimum — learn from cycle 1 | Writes observations from first cycle. Noisy early but incremental constraint keeps it manageable. | ✓ |
| 3-cycle warmup | First 3 cycles: observations only, no rules. After 3: start writing rules. | |
| 5-cycle warmup | Conservative: 5 cycles of observation. Most data but delays feedback loop. | |

**User's choice:** No minimum — learn from cycle 1 (Recommended)
**Notes:** None

### Q4: Should the Strategy Updater read strategy history to detect drift?

| Option | Description | Selected |
|--------|-------------|----------|
| No — rely on incremental constraint | Incremental-only + git history is sufficient. No active drift comparison. | ✓ |
| Yes — compare to N cycles ago | Read strategy from 5-10 cycles ago, flag significant drift. More robust but adds complexity. | |

**User's choice:** No — rely on incremental constraint (Recommended)
**Notes:** None

---

## Claude's Discretion

- Git commit message format for strategy updates
- Strategy Updater maxTurns setting
- Exact JSON schema for strategy_update.json
- Strategy section formatting
- Per-cycle report format refinements
- How Updater decides which suggestions to act on vs defer
- Git versioning approach (user skipped this discussion area)

## Deferred Ideas

None — discussion stayed within phase scope
