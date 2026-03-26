# Phase 3: Strategy Evolution - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Self-improving strategy document with per-cycle reports and git versioning. After each trading cycle, a dedicated sub-agent updates `state/strategy.md` based on Reviewer analysis, with an auditable history of strategy changes via git commits. The agent reads this strategy at the start of every subsequent cycle. Scheduling (STRT-07) and safety hardening belong in Phase 4.

</domain>

<decisions>
## Implementation Decisions

### Strategy Update Mechanism
- **D-01:** New "Strategy Updater" sub-agent (`.claude/agents/strategy-updater.md`) spawned after Reviewer step. Clean separation of concerns — matches the existing multi-agent pattern from Phase 2.
- **D-02:** Strategy Updater reads `reviewer_output.json` (learnings + strategy_suggestions) plus current `state/strategy.md`. Reviewer output only — no full cycle data. Reviewer already synthesized the cycle.
- **D-03:** Strategy Updater handles git commit of strategy changes. Runs `git add state/strategy.md && git commit` with a dated message. Self-contained update lifecycle.
- **D-04:** Strategy Updater writes structured JSON output (`state/cycles/{cycle_id}/strategy_update.json`) listing what changed and why. Audit trail + main agent can validate the update.
- **D-05:** trading-cycle.md gains a new Step 7 (after Reviewer) that spawns the Strategy Updater sub-agent. The existing "NEVER modify strategy.md" constraint is removed.

### Core Principles Protection
- **D-06:** Core Principles live in a separate file: `state/core-principles.md`. Human-edited, never touched by the agent. Strategy Updater writes to `state/strategy.md` sections only. Main agent reads both files at cycle start.
- **D-07:** Agent proposes Core Principles after observing initial cycles. User reviews and locks them into `state/core-principles.md`. Until user writes principles, the file starts with a placeholder noting "To be defined after initial cycles."
- **D-08:** Strategy Updater prompt explicitly states: "NEVER modify or reference core-principles.md. That file is read-only for the human operator."

### Evolution Guardrails
- **D-09:** Incremental updates only — each cycle adds/refines 1-3 rules maximum. Cannot delete existing rules. Can only add new rules, refine existing ones, or mark them as "under review." Prevents wild strategy swings.
- **D-10:** Parameter adjustments are suggestions only. Updater writes parameter change suggestions to strategy.md (e.g., "Consider raising MIN_EDGE_THRESHOLD to 0.12"). Does NOT modify .env or any config. User or Phase 4 mechanism applies them.
- **D-11:** No minimum cycle warmup — agent writes observations and rules from cycle 1. Early observations may be noisy; incremental-only constraint keeps them manageable.
- **D-12:** No git history drift detection. Rely on the incremental-only constraint plus git history as passive audit trail. No active drift comparison.

### Claude's Discretion
- Git commit message format for strategy updates
- Strategy Updater `maxTurns` setting (empirical testing needed)
- Exact JSON schema for `strategy_update.json`
- Strategy section formatting and content structure within the 4 domains (market selection, analysis approach, risk parameters, entry/exit rules)
- Per-cycle report format refinements (Reviewer already has a working template from Phase 2)
- How the Updater decides which Reviewer suggestions to act on vs defer

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Requirements & Success Criteria
- `.planning/REQUIREMENTS.md` — STRT-01 through STRT-06 (Phase 3 requirements), STRT-07 mapped to Phase 4
- `.planning/ROADMAP.md` — Phase 3 success criteria (5 acceptance tests)

### Phase 2 Decisions (agent layer interface)
- `.planning/phases/02-agent-layer/02-CONTEXT.md` — D-01 through D-12: orchestration flow, state directory layout, sub-agent patterns, report format
- `.claude/agents/trading-cycle.md` — Main orchestration agent that Phase 3 extends with new Step 7
- `.claude/agents/reviewer.md` — Reviewer agent that produces the inputs Strategy Updater consumes

### Existing State Infrastructure
- `state/strategy.md` — Current strategy document (5-section skeleton, placeholder content)
- `state/reports/` — Cycle reports directory (Reviewer writes here)
- `state/cycles/` — Per-cycle intermediate outputs directory

### Codebase Architecture
- `.planning/codebase/CONVENTIONS.md` — Naming patterns, code style, agent conventions
- `.planning/codebase/STRUCTURE.md` — Current file layout

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `state/strategy.md` — Already exists with 5 sections matching STRT-03 domains (Core Principles, Market Selection Rules, Analysis Approach, Risk Parameters, Trade Entry/Exit Rules). Placeholder content ready to be filled.
- `.claude/agents/reviewer.md` — Already outputs `strategy_suggestions` and `learnings` in `reviewer_output.json`. This is the primary input for the Strategy Updater.
- `.claude/agents/trading-cycle.md` — Already reads strategy.md + 3 most recent reports at cycle start (Step 0). Phase 3 adds Step 7 for strategy update.
- Sub-agent pattern established: `.claude/agents/*.md` with frontmatter (name, description, tools, model, maxTurns, permissionMode).

### Established Patterns
- Sub-agents write structured JSON to `state/cycles/{cycle_id}/` (Phase 2 D-04)
- Sequential pipeline with validation between steps (Phase 2 D-01)
- Skip-and-continue on failures (Phase 2 D-02)
- Plain Python dict checks for schema validation (Phase 2 decision)
- `permissionMode: bypassPermissions` for all sub-agents

### Integration Points
- `trading-cycle.md` Step 7 (new) spawns Strategy Updater after Reviewer
- Strategy Updater reads `state/cycles/{cycle_id}/reviewer_output.json`
- Strategy Updater writes `state/strategy.md` and `state/cycles/{cycle_id}/strategy_update.json`
- Strategy Updater runs git commit on `state/strategy.md`
- `state/core-principles.md` (new file) read by main agent at cycle start alongside strategy.md

</code_context>

<specifics>
## Specific Ideas

- Agent proposes Core Principles after observing initial cycles, user reviews and locks them — not pre-seeded by anyone
- strategy.md already has the right 4-domain structure from STRT-03; the Updater writes within these sections
- Reviewer's `strategy_suggestions` field is the primary driver of strategy evolution — the Updater acts on these

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-strategy-evolution*
*Context gathered: 2026-03-26*
