---
phase: 2
slug: agent-layer
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | tests/ directory (existing) |
| **Quick run command** | `python -m pytest tests/ -x -q` |
| **Full suite command** | `python -m pytest tests/ -v` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `python -m pytest tests/ -x -q`
- **After every plan wave:** Run `python -m pytest tests/ -v`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | AGNT-01 | integration | `python -m pytest tests/test_agent_cycle.py -k scanner` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-02 | integration | `python -m pytest tests/test_agent_cycle.py -k analyst` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-03 | integration | `python -m pytest tests/test_agent_cycle.py -k debate` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-04 | integration | `python -m pytest tests/test_agent_cycle.py -k risk` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-05 | integration | `python -m pytest tests/test_agent_cycle.py -k planner` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-06 | integration | `python -m pytest tests/test_agent_cycle.py -k correlation` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-07 | integration | `python -m pytest tests/test_agent_cycle.py -k reviewer` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-08 | integration | `python -m pytest tests/test_agent_cycle.py -k report` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-09 | unit | `python -m pytest tests/test_schemas.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | AGNT-10 | integration | `python -m pytest tests/test_agent_cycle.py -k max_turns` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_agent_cycle.py` — integration test stubs for full cycle and sub-agent outputs
- [ ] `tests/test_schemas.py` — unit tests for JSON schema validation (AGNT-09)
- [ ] `tests/conftest.py` — shared fixtures for agent testing (mock tools, sample markets)

*Existing test infrastructure (pytest) covers framework needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Analyst uses web search for real-time data | AGNT-03 | Requires live API call to verify web search tool invocation | Run analyst agent on a current market, verify web search citations in output |
| Token cost logging accuracy | AGNT-10 | Claude Code token reporting is runtime-only | Run full cycle, compare logged token count against Claude Code session summary |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
