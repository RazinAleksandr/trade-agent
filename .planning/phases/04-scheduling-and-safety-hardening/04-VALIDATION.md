---
phase: 4
slug: scheduling-and-safety-hardening
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-03-27
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `tests/conftest.py` (fixtures for tmp_db, tmp_log, test_config, store) |
| **Quick run command** | `cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && pytest tests/ -x -q` |
| **Full suite command** | `cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run task-specific verify command from PLAN.md
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | SAFE-03, SAFE-04 | unit | `python -c "from lib.config import Config; c = Config(); assert c.cycle_interval == '4h'" && grep -q '.live-gate-pass' .gitignore` | ⬜ pending |
| 04-01-02 | 01 | 1 | SAFE-03, SAFE-04 | unit | `grep -q 'PolyApiException' lib/trading.py && grep -q 'GATE_BLOCKED' tools/execute_trade.py && pytest tests/test_trading.py -x -q` | ⬜ pending |
| 04-02-01 | 02 | 1 | STRT-07 | integration | `test -x run_cycle.sh && grep -q 'polymarket-cycle.pid' run_cycle.sh && grep -q '.cron-env' run_cycle.sh` | ⬜ pending |
| 04-02-02 | 02 | 1 | STRT-07 | unit | `pytest tests/test_scheduling.py -x -q` | ⬜ pending |
| 04-03-01 | 03 | 2 | SAFE-03 | integration | `python tools/enable_live.py --help 2>&1 && grep -q 'CONFIRM LIVE' tools/enable_live.py` | ⬜ pending |
| 04-03-02 | 03 | 2 | SAFE-01 to SAFE-05 | unit | `pytest tests/test_safety.py -x -v` | ⬜ pending |

*Status: ⬜ pending / ✅ green / ❌ red / ⚠️ flaky*

---

## Wave 0 Requirements

- No Wave 0 stub files needed. Each plan creates its own test files:
  - Plan 04-02 Task 2 creates `tests/test_scheduling.py` (TDD -- tests written first)
  - Plan 04-03 Task 2 creates `tests/test_safety.py` (TDD -- tests written first)
- No framework install needed (pytest 9.0.2 already available)
- Existing `tests/conftest.py` fixtures are reusable

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Cron entry fires on schedule | STRT-07 | Requires real crontab and time passage | Install with `tools/setup_schedule.py`, wait for interval, check `logs/cron-*.log` |
| Claude CLI headless execution | STRT-07 | Requires real Claude CLI and agent file | Run `run_cycle.sh` manually, verify log output |
| Interactive "CONFIRM LIVE" prompt | SAFE-03 | Requires real TTY input | Run `tools/enable_live.py` and type "CONFIRM LIVE" |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] No Wave 0 stub files needed (TDD tasks create their own test files)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
