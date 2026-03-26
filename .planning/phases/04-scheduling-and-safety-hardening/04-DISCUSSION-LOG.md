# Phase 4: Scheduling and Safety Hardening - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-27
**Phase:** 04-scheduling-and-safety-hardening
**Areas discussed:** Scheduling approach, Live trading gate

---

## Scheduling approach

### Scheduling mechanism

| Option | Description | Selected |
|--------|-------------|----------|
| Cron + shell script | Crontab entry runs a wrapper script that invokes `claude` CLI. Simple, proven, no Python daemon needed. | ✓ |
| APScheduler Python daemon | Long-running Python process using APScheduler that spawns `claude` CLI subprocess on schedule. More complex but gives programmatic control. | |
| You decide | Claude picks the simplest approach. | |

**User's choice:** Cron + shell script
**Notes:** Recommended as simplest approach. Works on both macOS (launchd reads crontab) and Linux.

### Overlap protection

| Option | Description | Selected |
|--------|-------------|----------|
| Lockfile guard | Wrapper script checks for a lockfile before starting. Skip and log warning if previous cycle running. | ✓ |
| No overlap protection | Just fire cycles on schedule, let them overlap. | |
| You decide | Claude picks based on architecture. | |

**User's choice:** Lockfile guard
**Notes:** Prevents duplicate trades and resource contention.

### Scheduling interval configuration

| Option | Description | Selected |
|--------|-------------|----------|
| Fixed interval via .env | Single CYCLE_INTERVAL env var (e.g., "4h", "1d", "30m"). Wrapper translates to crontab syntax. | ✓ |
| Raw crontab expression | User writes cron schedule directly. More flexible but requires cron syntax knowledge. | |
| Both options | CYCLE_INTERVAL for simple, CYCLE_CRON for advanced. Cron overrides interval if both set. | |

**User's choice:** Fixed interval via .env
**Notes:** Matches existing config pattern — all parameters in .env.

### Schedule setup method

| Option | Description | Selected |
|--------|-------------|----------|
| Setup script | `tools/setup_schedule.py` reads CYCLE_INTERVAL, installs/updates crontab. `--remove` flag to uninstall. | ✓ |
| Docs only | Document crontab entry, user installs manually. | |
| You decide | Claude picks. | |

**User's choice:** Setup script
**Notes:** Follows existing tools/ pattern.

---

## Live trading gate

### Gate location

| Option | Description | Selected |
|--------|-------------|----------|
| Separate gate tool | `tools/enable_live.py` — checks paper P&L, displays it, requires "CONFIRM LIVE", writes gate-pass file. | ✓ |
| In execute_trade.py | Check paper P&L before every live trade. Blocks at trade-time. | |
| Agent-level check | trading-cycle.md agent checks at cycle start. Decision in agent prompt. | |

**User's choice:** Separate gate tool
**Notes:** Clean separation from trade execution logic.

### Minimum cycle count

| Option | Description | Selected |
|--------|-------------|----------|
| Configurable via .env | MIN_PAPER_CYCLES env var (default 10). Queries SQLite for cycle count and aggregate P&L. | ✓ |
| Hardcoded minimum | Fixed at 10 cycles. Simpler but less flexible. | |
| You decide | Claude picks. | |

**User's choice:** Configurable via .env
**Notes:** Must have >= N cycles AND positive cumulative P&L to pass.

### Gate persistence

| Option | Description | Selected |
|--------|-------------|----------|
| One-time gate file | `.live-gate-pass` file after confirmation. Survives restarts. Delete to re-lock. | ✓ |
| Per-session confirmation | Must confirm every scheduled run. More cautious but defeats unattended operation. | |

**User's choice:** One-time gate file
**Notes:** Delete the file to re-lock; re-run enable_live.py to re-verify conditions.

---

## Claude's Discretion

- Credential refresh implementation (SAFE-04) — retry logic, backoff strategy
- Wrapper script structure and logging
- Lockfile implementation (flock vs PID)
- CYCLE_INTERVAL parsing
- Gate-pass file format and location
- Test coverage for already-satisfied requirements (SAFE-01, SAFE-02, SAFE-05)

## Deferred Ideas

None — discussion stayed within phase scope.
