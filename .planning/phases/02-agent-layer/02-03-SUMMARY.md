---
phase: 02-agent-layer
plan: 03
subsystem: agent
tags: [claude-code, sub-agents, risk-management, kelly-criterion, correlation-detection, trade-planning, cycle-review]

# Dependency graph
requires:
  - phase: 02-01
    provides: State directory structure, agent schemas, cycle state management
provides:
  - Risk Manager sub-agent with Kelly sizing, correlation detection, and exposure limits
  - Planner sub-agent that synthesizes all prior outputs into executable trade plan
  - Reviewer sub-agent that analyzes cycle results and writes reports
affects: [02-04, 03-strategy-evolution]

# Tech tracking
tech-stack:
  added: []
  patterns: [sub-agent YAML frontmatter convention, JSON file passing between agents, correlation detection via semantic analysis]

key-files:
  created:
    - .claude/agents/risk-manager.md
    - .claude/agents/planner.md
    - .claude/agents/reviewer.md
  modified:
    - .gitignore

key-decisions:
  - "Unignored .claude/agents/ in .gitignore to allow tracking agent definitions while keeping other .claude/ files private"
  - "Risk Manager uses correlation_factor of 0.5 for correlated positions per AGNT-06"
  - "Planner maxTurns: 8, Risk Manager and Reviewer maxTurns: 10 per research recommendations"

patterns-established:
  - "Sub-agent definitions: YAML frontmatter with name, description, tools, model, maxTurns, permissionMode"
  - "Tool invocation pattern: cd to project root, activate venv, run Python tool with --pretty flag"
  - "Output path pattern: agents write JSON to state/cycles/{cycle_id}/ path specified in task prompt"

requirements-completed: [AGNT-05, AGNT-06, AGNT-07, AGNT-08, AGNT-10]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 02 Plan 03: Risk Manager, Planner, and Reviewer Sub-Agents Summary

**Risk Manager with Kelly sizing and correlation detection, Planner with strategy-aware trade planning, and Reviewer with dual JSON/markdown cycle reporting**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T14:54:20Z
- **Completed:** 2026-03-26T14:58:06Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Risk Manager sub-agent with Kelly criterion sizing, correlation detection (AGNT-06), and exposure limit enforcement (AGNT-05)
- Planner sub-agent that reads strategy.md and all prior pipeline outputs to create executable trade plan (AGNT-07)
- Reviewer sub-agent that produces both structured JSON review and human-readable markdown cycle report (AGNT-08, D-11)
- All three agents have maxTurns limits in YAML frontmatter (AGNT-10)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create Risk Manager sub-agent definition** - `24fc6ad` (feat)
2. **Task 2: Create Planner and Reviewer sub-agent definitions** - `af9d06a` (feat)

## Files Created/Modified
- `.claude/agents/risk-manager.md` - Risk Manager agent definition with Kelly sizing, correlation detection, and structured JSON output
- `.claude/agents/planner.md` - Planner agent that synthesizes strategy + all prior outputs into trade_plan.json
- `.claude/agents/reviewer.md` - Reviewer agent that writes reviewer_output.json and cycle report markdown
- `.gitignore` - Added negation pattern to track .claude/agents/ while keeping other .claude/ files private

## Decisions Made
- Unignored `.claude/agents/` in `.gitignore` (the directory was blocked by the existing `.claude/` ignore rule, but agent definitions must be tracked)
- Risk Manager uses `correlation_factor` of 0.5 (halves position size for correlated markets) per Pattern 4 in research
- Minimum order size threshold set to 5.0 USDC in Risk Manager approval logic
- Planner maxTurns: 8, Risk Manager and Reviewer maxTurns: 10 (from research recommendations)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Unignored .claude/agents/ in .gitignore**
- **Found during:** Task 1 (Risk Manager commit)
- **Issue:** `.claude/` was in `.gitignore`, preventing agent definition files from being tracked
- **Fix:** Added `!.claude/agents/` negation pattern to `.gitignore` after the `.claude/` rule
- **Files modified:** `.gitignore`
- **Verification:** `git add -f .claude/agents/risk-manager.md` succeeded after change
- **Committed in:** 24fc6ad (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Essential fix to allow agent definitions to be version-controlled. No scope creep.

## Issues Encountered
None beyond the gitignore blocking issue documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all three agent definitions are complete with full instructions, output schemas, and edge case handling.

## Next Phase Readiness
- All 3 decision/review sub-agents created: Risk Manager, Planner, Reviewer
- Combined with Scanner and Analyst from plan 02-02, all 5 sub-agents will be available for main orchestration (plan 02-04)
- Agent definitions reference Phase 1 CLI tools by correct path and argument format
- JSON output schemas match the inter-agent contracts defined in 02-RESEARCH.md

---
*Phase: 02-agent-layer*
*Completed: 2026-03-26*
