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
| **Config file** | none — existing `tests/` directory |
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

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INST-01 | unit | `python -m pytest tests/test_discover_markets.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-02 | unit | `python -m pytest tests/test_discover_markets.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-03 | unit | `python -m pytest tests/test_discover_markets.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-04 | unit | `python -m pytest tests/test_execute_trade.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-05 | unit | `python -m pytest tests/test_execute_trade.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-06 | unit | `python -m pytest tests/test_execute_trade.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-07 | unit | `python -m pytest tests/test_portfolio.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-08 | unit | `python -m pytest tests/test_portfolio.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-09 | unit | `python -m pytest tests/test_execute_trade.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-10 | integration | `python -m pytest tests/test_cli.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-11 | integration | `python -m pytest tests/test_cli.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-12 | unit | `python -m pytest tests/test_config.py -x -q` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INST-13 | unit | `python -m pytest tests/test_logging.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_discover_markets.py` — stubs for INST-01, INST-02, INST-03
- [ ] `tests/test_execute_trade.py` — stubs for INST-04, INST-05, INST-06, INST-09
- [ ] `tests/test_portfolio.py` — stubs for INST-07, INST-08
- [ ] `tests/test_cli.py` — stubs for INST-10, INST-11
- [ ] `tests/test_config.py` — stubs for INST-12
- [ ] `tests/test_logging.py` — stubs for INST-13
- [ ] `tests/conftest.py` — shared fixtures (mock API responses, temp DB)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SIGINT graceful shutdown | INST-11 | Requires signal sending during execution | Run tool, send Ctrl+C, verify clean exit |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
