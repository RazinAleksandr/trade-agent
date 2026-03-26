---
phase: 01-instrument-layer
plan: 01
subsystem: foundation
tags: [python, dataclass, sqlite, logging, config, dotenv, signals]

# Dependency graph
requires: []
provides:
  - "lib/ Python package with 7 modules (init, config, models, db, logging_setup, signals, errors)"
  - "Config dataclass with .env loading and CLI override support (15 parameters)"
  - "Market, TradeSignal, OrderResult dataclasses with to_dict()"
  - "DataStore class with 5-table SQLite schema and full CRUD"
  - "Dual logging (stderr console + JSON file) via get_logger()"
  - "Graceful shutdown handler for SIGINT/SIGTERM"
  - "Structured JSON error output to stderr with exit codes"
  - "Pytest infrastructure with shared fixtures"
affects: [01-02, 01-03, 01-04, 01-05, 01-06]

# Tech tracking
tech-stack:
  added: [pytest]
  patterns: [dataclass-config, dual-logging, json-stderr-errors, cli-override-precedence]

key-files:
  created:
    - lib/__init__.py
    - lib/config.py
    - lib/models.py
    - lib/db.py
    - lib/logging_setup.py
    - lib/signals.py
    - lib/errors.py
    - tests/conftest.py
    - tests/test_config.py
    - tests/test_db.py
    - pytest.ini
  modified: []

key-decisions:
  - "Config uses @dataclass with load_config() factory function, not module-level globals"
  - "Logging sends console output to stderr (stdout reserved for JSON tool output per D-02)"
  - "DataStore accepts explicit db_path parameter rather than importing from config module"
  - "Trade schema extended with neg_risk and fill_price columns for v2 auditing requirements"

patterns-established:
  - "Config precedence: CLI args > env vars > dataclass defaults"
  - "All lib/ modules import from lib.* namespace, never from v1 root modules"
  - "Tests use temp files via fixtures for database and log isolation"
  - "Structured errors via JSON to stderr with typed exit codes"

requirements-completed: [INST-10, INST-11, INST-12, INST-13]

# Metrics
duration: 4min
completed: 2026-03-26
---

# Phase 1 Plan 01: Foundation Summary

**lib/ package with Config dataclass (.env + CLI override), SQLite DataStore (5 tables, neg_risk/fill_price columns), dual logging (stderr + JSON file), SIGINT/SIGTERM handler, and 14 passing pytest tests**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-26T10:27:48Z
- **Completed:** 2026-03-26T10:32:08Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments
- Created lib/ package with 7 modules providing shared foundation for all CLI tools
- Config system with 15 parameters supporting .env defaults, env var overrides, and CLI arg precedence
- DataStore with adapted SQLite schema (neg_risk + fill_price columns for v2 auditing)
- 14 passing tests covering config loading, dual logging, and all database CRUD operations

## Task Commits

Each task was committed atomically:

1. **Task 1: Create lib/ package with config, models, errors, logging, and signals modules** - `3afc57f` (feat)
2. **Task 2: Create lib/db.py SQLite persistence and test infrastructure** - `741bf34` (feat)

## Files Created/Modified
- `lib/__init__.py` - Package marker
- `lib/config.py` - Config dataclass with load_config() supporting .env + CLI overrides
- `lib/models.py` - Market, TradeSignal, OrderResult dataclasses with to_dict()
- `lib/db.py` - DataStore class with 5-table SQLite schema and full CRUD operations
- `lib/logging_setup.py` - Dual logger (stderr console + JSON file), JsonFormatter
- `lib/signals.py` - SIGINT/SIGTERM graceful shutdown handler
- `lib/errors.py` - Structured JSON error output to stderr with exit codes
- `tests/conftest.py` - Shared pytest fixtures (tmp_db_path, tmp_log_path, test_config, store)
- `tests/test_config.py` - 5 tests for config defaults, env/CLI overrides, dual logging
- `tests/test_db.py` - 9 tests for table creation, CRUD, position upsert/close, exposure, stats, neg_risk
- `pytest.ini` - Pytest configuration with testpaths=tests

## Decisions Made
- Config uses `@dataclass` with factory function `load_config()` instead of module-level globals (cleaner testability, explicit initialization)
- Console logging goes to `sys.stderr` (stdout reserved for JSON tool output per D-02)
- DataStore accepts explicit `db_path` parameter (no hidden config import, explicit dependency)
- Trade table extended with `neg_risk INTEGER DEFAULT 0` and `fill_price REAL` columns per D-09 auditing needs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_config_defaults to isolate from .env file**
- **Found during:** Task 2 (test execution)
- **Issue:** test_config_defaults failed because .env file in repo set PRIVATE_KEY, so defaults assertion failed
- **Fix:** Added monkeypatch.delenv() for all config env vars in test_config_defaults to test pure dataclass defaults
- **Files modified:** tests/test_config.py
- **Verification:** All 14 tests pass
- **Committed in:** 741bf34 (Task 2 commit)

**2. [Rule 1 - Bug] Fixed test_tables_created to exclude sqlite_sequence internal table**
- **Found during:** Task 2 (test execution)
- **Issue:** SQLite auto-creates sqlite_sequence table for AUTOINCREMENT columns, causing table count assertion to fail
- **Fix:** Added filter to exclude table names starting with "sqlite_" before asserting
- **Files modified:** tests/test_db.py
- **Verification:** All 14 tests pass
- **Committed in:** 741bf34 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both auto-fixes are standard test isolation corrections. No scope creep.

## Issues Encountered
None beyond the test isolation fixes documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- lib/ package complete with all 7 modules importable
- All subsequent plans (01-02 through 01-06) can import from lib.config, lib.models, lib.db, lib.logging_setup, lib.signals, lib.errors
- Pytest infrastructure ready with shared fixtures for all future test files
- No blockers for wave 1 parallel plans (01-02)

## Self-Check: PASSED

All 11 created files verified present. Both task commits (3afc57f, 741bf34) verified in git log.

---
*Phase: 01-instrument-layer*
*Completed: 2026-03-26*
