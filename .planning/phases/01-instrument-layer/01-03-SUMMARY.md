---
phase: 01-instrument-layer
plan: 03
subsystem: strategy
tags: [python, kelly-criterion, edge-calculation, position-sizing, cli-tools, argparse, json]

# Dependency graph
requires:
  - phase: 01-01
    provides: "lib/ package with config, models, errors modules"
provides:
  - "lib/strategy.py with kelly_criterion(), calculate_edge(), calculate_position_size()"
  - "tools/calculate_edge.py CLI tool for edge calculation (INST-03)"
  - "tools/calculate_kelly.py CLI tool for Kelly sizing (INST-04)"
  - "19 passing tests for all strategy functions"
affects: [01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: []
  patterns: [sys-path-fix-for-tools, pure-function-strategy, json-cli-output]

key-files:
  created:
    - lib/strategy.py
    - tools/calculate_edge.py
    - tools/calculate_kelly.py
    - tests/test_kelly.py
  modified: []

key-decisions:
  - "Strategy module is pure math functions (no Config import, no API calls) for maximum testability"
  - "CLI tools add sys.path fix to import lib/ from tools/ subdirectory"
  - "calculate_position_size returns dict (not dataclass) for direct JSON serialization in CLI tools"

patterns-established:
  - "tools/ CLI scripts use sys.path.insert(0, project_root) to resolve lib/ imports"
  - "Pure-math modules accept all parameters explicitly (no global config dependency)"
  - "CLI tools validate inputs before calling lib/ functions, using error_exit() for structured errors"

requirements-completed: [INST-03, INST-04]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 1 Plan 03: Strategy & Kelly Summary

**Kelly criterion with quarter-Kelly default, edge calculation, position sizing with 5 USDC minimum, and two CLI tool wrappers outputting JSON**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T10:35:56Z
- **Completed:** 2026-03-26T10:39:37Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Implemented Kelly criterion cherry-picked from v1 with correct math (max(0.0, kelly), quarter-Kelly default)
- Edge calculation as simple rounded subtraction (estimated_prob - market_price)
- Position sizing with max cap, bankroll limit, and SAFE-05 minimum order size (5 USDC)
- Two CLI tools with argparse, JSON output, input validation, --pretty and --help support
- 19 passing tests covering all boundary conditions

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Add failing tests for kelly criterion** - `334a897` (test)
2. **Task 1 (GREEN): Implement lib/strategy.py** - `f924ed4` (feat)
3. **Task 2: Add calculate_edge and calculate_kelly CLI tools** - `82a44ad` (feat)

_Note: Task 1 was TDD with RED/GREEN commits._

## Files Created/Modified
- `lib/strategy.py` - kelly_criterion(), calculate_edge(), calculate_position_size() pure math
- `tools/calculate_edge.py` - CLI tool: --estimated-prob, --market-price, outputs edge/direction JSON
- `tools/calculate_kelly.py` - CLI tool: --estimated-prob, --market-price, --bankroll, --kelly-fraction, --max-position
- `tests/test_kelly.py` - 19 tests for kelly, edge, and position sizing

## Decisions Made
- Strategy module has zero dependency on Config (all parameters are explicit function arguments). This makes functions independently testable and CLI tools pass values explicitly.
- calculate_position_size returns a dict rather than a dataclass, enabling direct `**position` spread into JSON output without conversion.
- CLI tools use `sys.path.insert(0, project_root)` to resolve lib/ imports when invoked from any directory, since Python adds the script's directory (tools/) rather than cwd to sys.path.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added sys.path fix for lib/ imports in tools/**
- **Found during:** Task 2 (CLI tool creation)
- **Issue:** Running `python tools/calculate_edge.py` failed with `ModuleNotFoundError: No module named 'lib'` because Python adds the script directory (tools/) to sys.path, not the project root
- **Fix:** Added `sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))` at top of both CLI tools
- **Files modified:** tools/calculate_edge.py, tools/calculate_kelly.py
- **Verification:** Both tools run successfully from any working directory
- **Committed in:** 82a44ad (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Standard Python path fix required for tools/ subdirectory pattern. No scope creep.

## Issues Encountered
None beyond the sys.path fix documented above.

## User Setup Required
None - no external service configuration required.

## Known Stubs
None - all functions are fully implemented with no placeholder data or TODO markers.

## Next Phase Readiness
- lib/strategy.py provides kelly_criterion, calculate_edge, calculate_position_size for use by later plans
- tools/ directory established with first two CLI tools (calculate_edge, calculate_kelly)
- sys.path pattern established for all future tools/ scripts
- No blockers for Plans 04-06

## Self-Check: PASSED

All 4 created files verified present. All 3 task commits (334a897, f924ed4, 82a44ad) verified in git log.

---
*Phase: 01-instrument-layer*
*Completed: 2026-03-26*
