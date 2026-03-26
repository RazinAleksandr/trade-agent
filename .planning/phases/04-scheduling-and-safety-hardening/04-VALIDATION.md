---
phase: 4
slug: scheduling-and-safety-hardening
status: draft
nyquist_compliant: false
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

- **After every task commit:** Run `pytest tests/test_safety.py tests/test_scheduling.py -x -q`
- **After every plan wave:** Run `pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SAFE-01 | unit | `pytest tests/test_safety.py::test_paper_trading_default -x` | Wave 0 | ⬜ pending |
| 04-01-02 | 01 | 1 | SAFE-02 | unit | `pytest tests/test_safety.py::test_paper_fill_realistic_pricing -x` | Wave 0 | ⬜ pending |
| 04-01-03 | 01 | 1 | SAFE-05 | unit | `pytest tests/test_safety.py::test_order_normalization -x` | Wave 0 | ⬜ pending |
| 04-02-01 | 02 | 1 | SAFE-04 | unit | `pytest tests/test_safety.py::test_credential_refresh_on_401 -x` | Wave 0 | ⬜ pending |
| 04-02-02 | 02 | 1 | SAFE-04 | unit | `pytest tests/test_safety.py::test_non_401_errors_propagate -x` | Wave 0 | ⬜ pending |
| 04-03-01 | 03 | 2 | SAFE-03 | unit | `pytest tests/test_safety.py::test_gate_blocks_insufficient_cycles -x` | Wave 0 | ⬜ pending |
| 04-03-02 | 03 | 2 | SAFE-03 | unit | `pytest tests/test_safety.py::test_gate_allows_on_conditions_met -x` | Wave 0 | ⬜ pending |
| 04-03-03 | 03 | 2 | SAFE-03 | unit | `pytest tests/test_safety.py::test_execute_trade_blocks_without_gate -x` | Wave 0 | ⬜ pending |
| 04-04-01 | 04 | 3 | STRT-07 | unit | `pytest tests/test_scheduling.py::test_interval_to_cron -x` | Wave 0 | ⬜ pending |
| 04-04-02 | 04 | 3 | STRT-07 | unit | `pytest tests/test_scheduling.py::test_crontab_management -x` | Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_safety.py` — stubs for SAFE-01, SAFE-02, SAFE-03, SAFE-04, SAFE-05
- [ ] `tests/test_scheduling.py` — stubs for STRT-07 (interval parsing, crontab management)
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

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
