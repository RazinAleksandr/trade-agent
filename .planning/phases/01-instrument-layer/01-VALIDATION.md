---
phase: 1
slug: instrument-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pytest.ini` (created in Plan 01-01, Task 2) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~10 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 01-01-T1 | 01-01 | 1 | INST-11, INST-12, INST-13 | unit | `python -c "from lib.config import Config, load_config; ..."` | (import check) | pending |
| 01-01-T2 | 01-01 | 1 | INST-10, INST-11, INST-13 | unit | `python -m pytest tests/test_config.py tests/test_db.py -x -v` | tests/test_config.py, tests/test_db.py | pending |
| 01-02-T1 | 01-02 | 2 | INST-01, INST-02, INST-09 | unit | `python -m pytest tests/test_market_data.py tests/test_pricing.py -x -v -k "not integration"` | tests/test_market_data.py, tests/test_pricing.py | pending |
| 01-02-T2 | 01-02 | 2 | INST-01, INST-02 | integration | `python -m pytest tests/test_cli.py -x -v` | tests/test_cli.py | pending |
| 01-03-T1 | 01-03 | 2 | INST-03, INST-04 | unit (TDD) | `python -m pytest tests/test_kelly.py -x -v` | tests/test_kelly.py | pending |
| 01-03-T2 | 01-03 | 2 | INST-03, INST-04 | integration | `python tools/calculate_edge.py --estimated-prob 0.65 --market-price 0.50` | (CLI output check) | pending |
| 01-04-T1 | 01-04 | 3 | INST-05, INST-06 | unit | `python -m pytest tests/test_trading.py -x -v` | tests/test_trading.py | pending |
| 01-04-T2 | 01-04 | 3 | INST-05, INST-06 | integration | `python tools/execute_trade.py --help` | (CLI help check) | pending |
| 01-05-T1 | 01-05 | 3 | INST-07, INST-08 | unit | `python -m pytest tests/test_portfolio.py -x -v` | tests/test_portfolio.py | pending |
| 01-05-T2 | 01-05 | 3 | INST-07, INST-08 | integration | `python tools/get_portfolio.py --help && python tools/check_resolved.py --help` | (CLI help check) | pending |
| 01-06-T1 | 01-06 | 4 | ALL INST | integration | `python -m pytest tests/ -v --timeout=30 && all 7 tools --help` | tests/* | pending |
| 01-06-T2 | 01-06 | 4 | ALL INST | checkpoint | Human verification of end-to-end functionality | N/A | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

Test files created by their respective plans (not a separate Wave 0 step):

- [x] `tests/conftest.py` — shared fixtures (Plan 01-01, Task 2)
- [x] `pytest.ini` — pytest config (Plan 01-01, Task 2)
- [ ] `tests/test_config.py` — config loading tests (Plan 01-01, Task 2)
- [ ] `tests/test_db.py` — SQLite DataStore tests (Plan 01-01, Task 2)
- [ ] `tests/test_market_data.py` — Gamma API parsing tests (Plan 01-02, Task 1)
- [ ] `tests/test_pricing.py` — CLOB pricing tests (Plan 01-02, Task 1)
- [ ] `tests/test_cli.py` — CLI argument and output tests (Plan 01-02, Task 2)
- [ ] `tests/test_kelly.py` — Kelly criterion and edge tests (Plan 01-03, Task 1)
- [ ] `tests/test_trading.py` — Paper and live trade tests (Plan 01-04, Task 1)
- [ ] `tests/test_portfolio.py` — Portfolio and resolved market tests (Plan 01-05, Task 1)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SIGINT graceful shutdown | INST-12 | Requires signal sending during execution | Run tool, send Ctrl+C, verify clean exit |
| Live Gamma API integration | INST-01 | Requires network access | `python tools/discover_markets.py --limit 2 --pretty` |
| Human checkpoint (Plan 06) | ALL INST | End-to-end verification | Follow 01-06 Task 2 verification steps |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
