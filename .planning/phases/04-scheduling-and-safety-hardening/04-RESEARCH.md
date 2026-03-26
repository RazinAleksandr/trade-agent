# Phase 4: Scheduling and Safety Hardening - Research

**Researched:** 2026-03-27
**Domain:** Cron scheduling, credential refresh, live trading safety gates, shell scripting
**Confidence:** HIGH

## Summary

Phase 4 adds three capabilities to the existing instrument and agent layers: (1) cron-based scheduling with a shell wrapper script, (2) CLOB API credential refresh on 401 errors, and (3) a live trading gate requiring positive paper P&L. The decisions from CONTEXT.md are highly specific and prescriptive -- the research confirms they are technically sound and identifies the concrete implementation patterns for each.

The main technical risks are: macOS lacks `flock` (must use PID-file or `shlock` for lockfile guard), `PolyApiException` from py-clob-client carries `status_code` for 401 detection (verified in source), and `get_price()` is unauthenticated so credential refresh applies only to live trade execution. The existing codebase provides solid foundations -- `execute_live_trade()` already derives credentials per call, `validate_order()` handles SAFE-05, `get_fill_price()` handles SAFE-02, and `Config.paper_trading=True` handles SAFE-01.

**Primary recommendation:** Build three new files (`tools/setup_schedule.py`, `tools/enable_live.py`, `run_cycle.sh`) plus modify `lib/trading.py` for gate-pass check and credential retry. Add verification tests for already-satisfied SAFE-01/02/05. Keep implementation minimal -- no new dependencies.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Cron + shell wrapper script. A crontab entry runs a wrapper script that invokes the `claude` CLI with the trading-cycle agent. No Python daemon -- uses standard Unix scheduling.
- **D-02:** Lockfile guard to prevent overlapping cycles. Wrapper script checks for a lockfile before starting; if the previous cycle is still running, skip this invocation and log a warning. Use `flock` or PID-based lock.
- **D-03:** Fixed interval via `CYCLE_INTERVAL` env var in `.env` (e.g., `"4h"`, `"1d"`, `"30m"`). Wrapper script or setup tool translates to crontab syntax. Matches existing config pattern -- all parameters in `.env`.
- **D-04:** Setup script `tools/setup_schedule.py` reads `CYCLE_INTERVAL` from `.env` and installs/updates the crontab entry. `--remove` flag to uninstall. Follows the existing `tools/` CLI pattern.
- **D-05:** Separate gate tool `tools/enable_live.py` -- checks paper P&L, displays it, requires typing "CONFIRM LIVE", and writes a gate-pass file. Clean separation from trade execution logic.
- **D-06:** Configurable minimum paper cycles via `MIN_PAPER_CYCLES` env var (default 10). Gate tool queries SQLite for completed paper cycle count and aggregate P&L. Must have >= N cycles AND positive cumulative P&L to pass.
- **D-07:** One-time persistent gate file (`.live-gate-pass`). Written after successful confirmation. `execute_trade` checks for this file before placing live orders. Delete the file to re-lock. Re-run `enable_live.py` to re-verify conditions.
- **D-08:** Gate-pass check in `execute_trade.py` -- if `PAPER_TRADING=false` and no `.live-gate-pass` file exists, refuse to execute live trades with clear error message.
- **D-09:** Claude's discretion on credential refresh implementation (SAFE-04). Hook retry logic into `lib/trading.py` for 401 responses -- re-derive L2 credentials and retry the request. Also apply to `lib/pricing.py` for orderbook reads.
- **D-10:** SAFE-01 (paper default) -- already implemented in `Config.paper_trading = True`. Verify with test coverage.
- **D-11:** SAFE-02 (realistic paper pricing) -- already implemented via `get_fill_price()` in `lib/pricing.py` (best ask for buys, best bid for sells). Verify with test coverage.
- **D-12:** SAFE-05 (order normalization) -- already implemented in `validate_order()` in `lib/trading.py` (2 decimal places, min 5 USDC). Verify with test coverage.

### Claude's Discretion
- Wrapper script implementation details (shell script structure, logging format)
- Lockfile implementation approach (flock vs PID file)
- `CYCLE_INTERVAL` parsing and crontab translation logic
- Credential refresh retry count and backoff strategy
- Gate-pass file format and location
- How `enable_live.py` calculates aggregate paper P&L from SQLite
- Test coverage approach for already-satisfied requirements

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SAFE-01 | Paper trading is the default mode -- live trading requires explicit .env configuration change | Already implemented: `Config.paper_trading = True` in `lib/config.py`. Need verification tests only (D-10). |
| SAFE-02 | Paper mode simulates realistic spreads (not perfect fills) to prevent false edge measurement | Already implemented: `get_fill_price()` in `lib/pricing.py` queries best ask for buys, best bid for sells. Need verification tests only (D-11). |
| SAFE-03 | Live trading gate -- system requires positive paper P&L over configurable N cycles before allowing live mode | New implementation: `tools/enable_live.py` + gate-pass file + check in `execute_trade.py` (D-05 through D-08). |
| SAFE-04 | CLOB API credential refresh on 401 responses (L2 credentials expire) | New implementation: retry wrapper in `lib/trading.py` catching `PolyApiException` with `status_code == 401` (D-09). |
| SAFE-05 | Order amount normalization (max 2 decimal places for sell orders, minimum 5 USDC notional) | Already implemented: `validate_order()` in `lib/trading.py`. Need verification tests only (D-12). |
| STRT-07 | Configurable scheduling via cron (hourly, daily, custom interval) | New implementation: `run_cycle.sh` wrapper + `tools/setup_schedule.py` crontab manager (D-01 through D-04). |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **Python 3.12**, virtualenv at `.venv/`
- **Always run tests after changes:** `python tests/test_paper_trading.py` (also pytest available)
- **Never commit** `.env`, `trading.db`, `trading.log`, or `.claude/`
- **Paper trading is default** -- never change `PAPER_TRADING` to `false` without explicit user request
- **Keep modules flat** -- all `.py` files in project root, no sub-packages (but `lib/` is the current pattern)
- **All parameters in `config.py`** -- no hardcoded values in other modules
- **Secrets only in `.env`** -- loaded via `python-dotenv`, never in source code
- **Activate venv before running:** `source .venv/bin/activate`
- Tools in `tools/` are single-purpose CLI scripts with `argparse` and `sys.path.insert(0, project_root)`
- Console logging to stderr (stdout reserved for JSON tool output)

## Standard Stack

### Core (no new dependencies)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| py-clob-client | 0.34.6 (installed) | CLOB API client, credential derivation | Already in use; `PolyApiException.status_code` enables 401 detection |
| python-dotenv | >=1.0.0 (installed) | .env loading for new config vars | Already in use; `CYCLE_INTERVAL` and `MIN_PAPER_CYCLES` follow existing pattern |
| sqlite3 | stdlib | Paper P&L queries for gate tool | Already in use via `lib/db.py` |
| crontab | macOS/Linux system | Schedule trading cycles | D-01 locked decision; no Python cron library needed |
| argparse | stdlib | CLI for `setup_schedule.py` and `enable_live.py` | Existing tools/ pattern |

### No New Dependencies Required

This phase requires zero new pip packages. All functionality is achievable with:
- Standard library: `os`, `sys`, `subprocess`, `re`, `json`, `argparse`, `sqlite3`, `datetime`, `time`
- Already-installed: `py-clob-client`, `python-dotenv`
- System: `crontab`, `claude` CLI

## Architecture Patterns

### New File Layout
```
polymarket-agent/
  run_cycle.sh              # NEW: cron wrapper script (lockfile, logging, claude invocation)
  tools/
    setup_schedule.py       # NEW: crontab installer/remover (D-04)
    enable_live.py          # NEW: live trading gate tool (D-05)
    execute_trade.py        # MODIFIED: add gate-pass check (D-08)
  lib/
    config.py               # MODIFIED: add CYCLE_INTERVAL, MIN_PAPER_CYCLES fields
    trading.py              # MODIFIED: add 401 retry wrapper, gate-pass check
    db.py                   # MODIFIED: add get_paper_cycle_stats() method
  tests/
    test_scheduling.py      # NEW: tests for schedule setup, interval parsing
    test_safety.py          # NEW: tests for gate-pass, credential refresh, SAFE-01/02/05 verification
  .live-gate-pass           # RUNTIME: written by enable_live.py (gitignored)
```

### Pattern 1: PID-File Lockfile (for `run_cycle.sh`)
**What:** Use a PID file at `/tmp/polymarket-cycle.pid` to prevent overlapping cron invocations. macOS lacks `flock`; PID-based locking is the portable alternative.
**When to use:** Always -- D-02 requires lockfile guard.
**Implementation:**
```bash
#!/usr/bin/env bash
# run_cycle.sh -- Cron wrapper for trading cycle
LOCKFILE="/tmp/polymarket-cycle.pid"
LOGDIR="$(dirname "$0")/logs"
LOGFILE="$LOGDIR/cron-$(date +%Y%m%d-%H%M%S).log"

mkdir -p "$LOGDIR"

# PID-based lock check
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SKIP: Previous cycle still running (PID $OLD_PID)" >> "$LOGFILE"
        exit 0
    else
        echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) WARN: Stale lockfile removed (PID $OLD_PID)" >> "$LOGFILE"
        rm -f "$LOCKFILE"
    fi
fi

# Write our PID
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Run the trading cycle
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START: Trading cycle" >> "$LOGFILE"
cd "$(dirname "$0")"
claude --agent-file .claude/agents/trading-cycle.md \
    --print \
    --output-format text \
    "Run a trading cycle" \
    >> "$LOGFILE" 2>&1
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) END: Trading cycle (exit=$?)" >> "$LOGFILE"
```

### Pattern 2: CYCLE_INTERVAL to Crontab Translation
**What:** Parse human-friendly intervals into cron expressions.
**When to use:** `tools/setup_schedule.py` reads `.env` and installs crontab.
**Mapping:**
```
"30m"  -> "*/30 * * * *"     (every 30 minutes)
"1h"   -> "0 * * * *"        (every hour at :00)
"2h"   -> "0 */2 * * *"      (every 2 hours at :00)
"4h"   -> "0 */4 * * *"      (every 4 hours at :00)
"6h"   -> "0 */6 * * *"      (every 6 hours)
"12h"  -> "0 */12 * * *"     (every 12 hours)
"1d"   -> "0 0 * * *"        (daily at midnight)
```
**Implementation pattern:**
```python
import re

def interval_to_cron(interval: str) -> str:
    """Convert interval string (e.g. '4h', '30m', '1d') to cron expression."""
    match = re.match(r'^(\d+)(m|h|d)$', interval.strip().lower())
    if not match:
        raise ValueError(f"Invalid interval: {interval}. Use format like '30m', '4h', '1d'")
    value, unit = int(match.group(1)), match.group(2)
    if unit == 'm':
        if value < 1 or value > 59:
            raise ValueError(f"Minutes must be 1-59, got {value}")
        return f"*/{value} * * * *"
    elif unit == 'h':
        if value < 1 or value > 23:
            raise ValueError(f"Hours must be 1-23, got {value}")
        if value == 1:
            return "0 * * * *"
        return f"0 */{value} * * *"
    elif unit == 'd':
        if value != 1:
            raise ValueError("Only '1d' (daily) is supported for day intervals")
        return "0 0 * * *"
```

### Pattern 3: 401 Credential Refresh Retry
**What:** Wrap live trade execution to catch `PolyApiException(status_code=401)`, re-derive credentials, and retry once.
**When to use:** `execute_live_trade()` in `lib/trading.py`.
**Implementation:**
```python
from py_clob_client.exceptions import PolyApiException

def execute_live_trade(...) -> OrderResult:
    """Execute with one retry on 401 (expired credentials)."""
    size = round(size, 2)
    valid, msg = validate_order(price, size, order_min_size)
    if not valid:
        return OrderResult(order_id="", success=False, message=msg, is_paper=False)

    max_retries = 1
    for attempt in range(max_retries + 1):
        try:
            client = ClobClient(host, key=private_key, chain_id=chain_id, signature_type=0)
            creds = client.create_or_derive_api_creds()
            client.set_api_creds(creds)

            order_args = OrderArgs(token_id=token_id, price=price, size=size, side=BUY)
            signed = client.create_order(order_args)
            result = client.post_order(signed, OrderType.GTC)
            # ... record trade and return success ...
            break

        except PolyApiException as e:
            if e.status_code == 401 and attempt < max_retries:
                log.warning(f"401 received, re-deriving credentials (attempt {attempt + 1})")
                continue  # retry with fresh credentials
            log.error(f"Live trade failed: {e}")
            return OrderResult(order_id="", success=False, message=str(e), is_paper=False)
        except Exception as e:
            log.error(f"Live trade failed: {e}")
            return OrderResult(order_id="", success=False, message=str(e), is_paper=False)
```

### Pattern 4: Gate-Pass File Check
**What:** Before executing a live trade, verify `.live-gate-pass` file exists.
**When to use:** In `tools/execute_trade.py` when `is_live=True`.
**Implementation:**
```python
import os

GATE_PASS_FILE = ".live-gate-pass"

def check_gate_pass(project_root: str) -> tuple[bool, str]:
    """Check if the live trading gate pass exists."""
    gate_path = os.path.join(project_root, GATE_PASS_FILE)
    if not os.path.exists(gate_path):
        return (False, f"Live trading blocked: no gate pass file ({GATE_PASS_FILE}). "
                       f"Run 'python tools/enable_live.py' to verify paper P&L and enable live trading.")
    return (True, "")
```

### Pattern 5: Paper P&L Calculation from SQLite
**What:** Query trades table for paper trade cycle count and aggregate P&L.
**When to use:** `tools/enable_live.py` gate verification.
**Implementation approach:**
```python
def get_paper_cycle_stats(self) -> dict:
    """Get paper trading statistics for gate verification.

    Returns dict with:
    - cycle_count: number of distinct cycle dates with paper trades
    - total_pnl: aggregate realized P&L from closed paper positions
    - open_exposure: current open position cost basis
    """
    # Count distinct trading days/cycles (paper trades grouped by date)
    cycles = self.conn.execute(
        "SELECT COUNT(DISTINCT DATE(timestamp)) FROM trades WHERE is_paper = 1"
    ).fetchone()[0]

    # Aggregate realized P&L from closed positions
    result = self.conn.execute(
        "SELECT COALESCE(SUM(realized_pnl), 0) FROM positions WHERE status = 'closed'"
    ).fetchone()[0]

    return {"cycle_count": cycles, "total_pnl": result}
```

**Note:** Cycle counting is imprecise because the trades table records individual trades, not cycles. Two approaches:
1. Count distinct `DATE(timestamp)` from paper trades (coarse but simple)
2. Count cycle report files in `state/reports/` matching `cycle-*.md` pattern (more accurate, matches the agent's actual cycle count)

**Recommendation:** Use cycle report file count as the primary signal -- it directly represents completed trading cycles. The `state/reports/cycle-YYYYMMDD-HHMMSS.md` files are written by the Reviewer at the end of each cycle.

### Anti-Patterns to Avoid
- **APScheduler daemon:** D-01 explicitly chose cron over Python daemon. Do not add APScheduler.
- **Global state for credentials:** Do not cache ClobClient instances across calls. The existing pattern creates a fresh client per call, which naturally supports credential refresh.
- **Modifying `.env` programmatically from the gate tool:** The gate tool writes `.live-gate-pass`, not `.env`. Keep `.env` as human-edited only.
- **Fake fills on credential failure:** If 401 retry fails, the trade MUST fail -- never fall back to paper mode silently.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cron scheduling | Custom Python daemon or timer | System crontab via `crontab -l` / `crontab -` | Survives reboots, no process management, battle-tested |
| Interval parsing | Complex cron expression builder | Simple regex-based mapping (6 cases) | Only 3 units (m/h/d), limited valid ranges |
| Process locking | File-based mutex with timestamps | PID file + `kill -0` check | Standard Unix pattern, handles stale locks |
| Credential derivation | Manual API key creation | `client.create_or_derive_api_creds()` | py-clob-client handles the full derivation flow |

## Common Pitfalls

### Pitfall 1: macOS Lacks `flock`
**What goes wrong:** Shell script uses `flock` for lockfile, fails on macOS with "command not found".
**Why it happens:** `flock` is a Linux utility (util-linux). macOS has `shlock` but with different semantics.
**How to avoid:** Use PID-file approach: write `$$` to lockfile, check with `kill -0 $PID`. Clean up with `trap 'rm -f "$LOCKFILE"' EXIT`.
**Warning signs:** Script works on Linux CI but fails on dev Mac.

### Pitfall 2: Stale Lockfile After Crash
**What goes wrong:** Cron invocation crashes without removing lockfile. All subsequent invocations skip forever.
**Why it happens:** `trap EXIT` only runs on clean exit, not OOM kill or kill -9.
**How to avoid:** Check if PID in lockfile is still alive with `kill -0`. If not, remove stale lockfile and proceed.
**Warning signs:** Cycle stops running but no error in logs.

### Pitfall 3: Crontab PATH Issues
**What goes wrong:** Cron runs with minimal PATH. `claude` CLI, `python`, or other tools not found.
**Why it happens:** Cron uses `/usr/bin:/bin` by default, not the user's shell PATH.
**How to avoid:** Use absolute paths in `run_cycle.sh` for all commands. Include `PATH` export at top of script. `setup_schedule.py` should detect and embed the full PATH in the crontab entry.
**Warning signs:** Cron job runs but fails immediately with "command not found".

### Pitfall 4: PolyApiException vs Generic Exception
**What goes wrong:** Catch `Exception` broadly, missing the 401-specific `PolyApiException` with `status_code`.
**Why it happens:** `PolyApiException` inherits from `PolyException` which inherits from `Exception`. A broad `except Exception` catches it but loses status code info.
**How to avoid:** Catch `PolyApiException` FIRST (before general `Exception`), check `e.status_code == 401`.
**Warning signs:** Credential refresh never triggers even though 401s occur.

### Pitfall 5: get_price() Does NOT Need Auth
**What goes wrong:** Adding credential refresh to `lib/pricing.py` unnecessarily.
**Why it happens:** Assumption that all CLOB API calls require auth.
**How to avoid:** Verified in source: `ClobClient.get_price()` does NOT call `assert_level_2_auth()`. It is a public endpoint. Only `post_order()` and similar write operations require L2 auth. Credential refresh is only needed in `execute_live_trade()`.
**Warning signs:** Paper trading starts failing with auth errors when no auth is needed.

### Pitfall 6: Cycle Count Mismatch
**What goes wrong:** Gate tool counts paper trades as "cycles" but a single cycle may place 0 or many trades. Result: gate opens too early or never.
**Why it happens:** Trades table records individual trades, not cycles.
**How to avoid:** Count completed cycle reports in `state/reports/cycle-*.md` rather than trade rows. Each file represents one completed trading cycle regardless of how many trades it placed.
**Warning signs:** Gate opens after 10 trades (not 10 cycles), or never opens because 0-trade cycles don't count.

### Pitfall 7: Gate-Pass File Race Condition
**What goes wrong:** User deletes `.live-gate-pass` while a live trade is in progress.
**Why it happens:** File check and trade execution are not atomic.
**How to avoid:** Check gate pass once at the START of the trade execution flow, not per-order. This is acceptable because the gate is a human-facing safety measure, not a security boundary.
**Warning signs:** Trade partially executes then fails mid-way.

## Code Examples

### CYCLE_INTERVAL Config Extension
```python
# In lib/config.py - add to Config dataclass
@dataclass
class Config:
    # ... existing fields ...
    cycle_interval: str = "4h"
    min_paper_cycles: int = 10

# In _ENV_MAP
_ENV_MAP = {
    # ... existing mappings ...
    "CYCLE_INTERVAL": "cycle_interval",
    "MIN_PAPER_CYCLES": "min_paper_cycles",
}
```

### Gate-Pass Check in execute_trade.py
```python
# In tools/execute_trade.py, after determining is_live
if is_live:
    # Gate-pass check (D-08: SAFE-03)
    gate_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".live-gate-pass"
    )
    if not os.path.exists(gate_path):
        error_exit(
            "Live trading blocked: no gate pass. "
            "Run 'python tools/enable_live.py' first.",
            "GATE_BLOCKED",
            EXIT_CONFIG_ERROR,
        )
    # ... existing private key check ...
```

### Crontab Management in setup_schedule.py
```python
import subprocess
import re

CRON_MARKER = "# polymarket-trading-agent"

def get_current_crontab() -> str:
    """Get current user crontab, returning empty string if none."""
    result = subprocess.run(
        ["crontab", "-l"], capture_output=True, text=True
    )
    if result.returncode != 0:
        return ""
    return result.stdout

def install_crontab(cron_expr: str, script_path: str):
    """Install or update the trading cycle crontab entry."""
    current = get_current_crontab()
    # Remove existing polymarket entries
    lines = [l for l in current.splitlines()
             if CRON_MARKER not in l]
    # Add new entry
    lines.append(f"{cron_expr} {script_path} {CRON_MARKER}")
    new_crontab = "\n".join(lines) + "\n"
    subprocess.run(
        ["crontab", "-"], input=new_crontab, text=True, check=True
    )

def remove_crontab():
    """Remove polymarket trading cycle from crontab."""
    current = get_current_crontab()
    lines = [l for l in current.splitlines()
             if CRON_MARKER not in l]
    new_crontab = "\n".join(lines) + "\n" if lines else ""
    if new_crontab.strip():
        subprocess.run(
            ["crontab", "-"], input=new_crontab, text=True, check=True
        )
    else:
        subprocess.run(["crontab", "-r"], capture_output=True)
```

### 401 Detection Pattern
```python
# Source: verified from py_clob_client/exceptions.py and http_helpers/helpers.py
from py_clob_client.exceptions import PolyApiException

try:
    result = client.post_order(signed, OrderType.GTC)
except PolyApiException as e:
    if e.status_code == 401:
        # Credentials expired -- re-derive and retry
        log.warning("CLOB API returned 401, re-deriving credentials")
        # ... retry logic ...
    else:
        raise  # Non-auth error, propagate
```

### enable_live.py Gate Tool Structure
```python
#!/usr/bin/env python3
"""Live trading gate -- verify paper P&L before enabling live mode."""

import argparse
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.config import load_config
from lib.db import DataStore

GATE_PASS_FILE = ".live-gate-pass"


def count_completed_cycles(project_root: str) -> int:
    """Count completed cycle reports in state/reports/."""
    reports_dir = os.path.join(project_root, "state", "reports")
    if not os.path.isdir(reports_dir):
        return 0
    return len(glob.glob(os.path.join(reports_dir, "cycle-*.md")))


def get_paper_pnl(store: DataStore) -> float:
    """Get aggregate realized P&L from closed positions."""
    stats = store.get_strategy_stats()
    return stats.get("total_pnl", 0.0)


def main():
    parser = argparse.ArgumentParser(
        description="Verify paper P&L and enable live trading"
    )
    parser.add_argument("--revoke", action="store_true",
                        help="Remove gate pass (disable live trading)")
    args = parser.parse_args()

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    gate_path = os.path.join(project_root, GATE_PASS_FILE)

    if args.revoke:
        if os.path.exists(gate_path):
            os.remove(gate_path)
            print("Gate pass removed. Live trading disabled.")
        else:
            print("No gate pass found. Live trading already disabled.")
        return

    config = load_config()
    store = DataStore(db_path=config.db_path)

    try:
        cycles = count_completed_cycles(project_root)
        pnl = get_paper_pnl(store)

        print(f"\n{'='*50}")
        print("LIVE TRADING GATE VERIFICATION")
        print(f"{'='*50}")
        print(f"Completed paper cycles: {cycles}")
        print(f"Minimum required:       {config.min_paper_cycles}")
        print(f"Aggregate paper P&L:    ${pnl:.2f}")
        print(f"{'='*50}\n")

        if cycles < config.min_paper_cycles:
            print(f"BLOCKED: Need {config.min_paper_cycles - cycles} more paper cycles.")
            sys.exit(1)

        if pnl <= 0:
            print("BLOCKED: Paper P&L must be positive.")
            sys.exit(1)

        print("All conditions met. To enable live trading, type CONFIRM LIVE:")
        confirmation = input("> ").strip()

        if confirmation != "CONFIRM LIVE":
            print("Confirmation failed. Live trading NOT enabled.")
            sys.exit(1)

        # Write gate pass
        with open(gate_path, "w") as f:
            json.dump({
                "enabled_at": datetime.now(timezone.utc).isoformat(),
                "cycles_at_gate": cycles,
                "pnl_at_gate": pnl,
            }, f, indent=2)

        print(f"\nGate pass written to {GATE_PASS_FILE}")
        print("Live trading enabled. Delete the file to re-lock.")

    finally:
        store.close()
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| APScheduler daemon | System cron + wrapper script | D-01 decision | Simpler, no process management, survives reboots |
| `flock` for lockfile | PID file + `kill -0` | macOS compatibility | `flock` unavailable on macOS; PID-file is portable |
| Module-level cred cache | Fresh `ClobClient` per call | Phase 1 design | Natural credential refresh -- just retry the call |

**Deprecated/outdated:**
- APScheduler: Decision D-01 explicitly chose cron. Do not use.
- `flock`: Not available on macOS (this project's target platform). Use PID-file.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| crontab | Scheduling (STRT-07) | Yes | macOS built-in | -- |
| claude CLI | Trading cycle execution | Yes | (installed at /Users/aleksandrrazin/.nvm/...) | -- |
| flock | Lockfile guard (D-02) | No | -- | PID-file approach (recommended) |
| shlock | Lockfile guard (D-02) | Yes | macOS built-in | Could use, but PID-file is simpler |
| Python 3.12 | All tools | Yes | 3.12.9 | -- |
| pytest | Test execution | Yes | 9.0.2 | -- |
| py-clob-client | Credential refresh | Yes | 0.34.6 | -- |

**Missing dependencies with no fallback:**
- None -- all dependencies are available.

**Missing dependencies with fallback:**
- `flock` is unavailable on macOS. Use PID-file locking instead (standard Unix pattern, more portable).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `tests/conftest.py` (fixtures for tmp_db, tmp_log, test_config, store) |
| Quick run command | `cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && pytest tests/ -x -q` |
| Full suite command | `cd /Users/aleksandrrazin/work/polymarket-agent && source .venv/bin/activate && pytest tests/ -v` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SAFE-01 | Config.paper_trading defaults to True | unit | `pytest tests/test_safety.py::test_paper_trading_default -x` | Wave 0 |
| SAFE-02 | Paper buys fill at best ask, sells at best bid | unit | `pytest tests/test_safety.py::test_paper_fill_realistic_pricing -x` | Wave 0 (partially in test_trading.py/test_pricing.py) |
| SAFE-03 | Gate blocks live if cycles < N or P&L <= 0 | unit | `pytest tests/test_safety.py::test_gate_blocks_insufficient_cycles -x` | Wave 0 |
| SAFE-03 | Gate allows live when conditions met + CONFIRM LIVE typed | unit | `pytest tests/test_safety.py::test_gate_allows_on_conditions_met -x` | Wave 0 |
| SAFE-03 | execute_trade refuses live without gate pass | unit | `pytest tests/test_safety.py::test_execute_trade_blocks_without_gate -x` | Wave 0 |
| SAFE-04 | 401 triggers credential re-derivation and retry | unit | `pytest tests/test_safety.py::test_credential_refresh_on_401 -x` | Wave 0 |
| SAFE-04 | Non-401 errors propagate normally | unit | `pytest tests/test_safety.py::test_non_401_errors_propagate -x` | Wave 0 |
| SAFE-05 | Size rounded to 2 decimals, notional >= 5 USDC | unit | `pytest tests/test_safety.py::test_order_normalization -x` | Wave 0 (partially in test_trading.py) |
| STRT-07 | interval_to_cron converts correctly | unit | `pytest tests/test_scheduling.py::test_interval_to_cron -x` | Wave 0 |
| STRT-07 | Crontab entry installed/removed | unit | `pytest tests/test_scheduling.py::test_crontab_management -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest tests/test_safety.py tests/test_scheduling.py -x -q`
- **Per wave merge:** `pytest tests/ -v`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_safety.py` -- covers SAFE-01 through SAFE-05 (verification + new tests)
- [ ] `tests/test_scheduling.py` -- covers STRT-07 (interval parsing, crontab management)
- No framework install needed (pytest 9.0.2 already available)
- Existing `tests/conftest.py` fixtures are reusable

## Open Questions

1. **Claude CLI invocation flags for unattended cron execution**
   - What we know: `claude` CLI is available. The `--agent-file` flag exists for specifying agent definitions.
   - What's unclear: Exact flags for non-interactive, headless execution (no TTY). Need `--print` and possibly `--output-format text` to avoid interactive prompts.
   - Recommendation: Test `claude --agent-file .claude/agents/trading-cycle.md --print --output-format text "Run a trading cycle"` in development. Document the exact invocation in `run_cycle.sh`.

2. **Cycle counting precision**
   - What we know: Cycle reports in `state/reports/cycle-*.md` represent completed cycles. The trades table has per-trade rows.
   - What's unclear: For early usage, there may be few or zero completed cycles. How does the gate behave with 0 reports?
   - Recommendation: Count `state/reports/cycle-*.md` files. If 0, gate blocks with clear message saying "No completed paper cycles found."

3. **Gate-pass file location and .gitignore**
   - What we know: `.live-gate-pass` should be in project root per D-07.
   - What's unclear: Whether it is already in `.gitignore`.
   - Recommendation: Add `.live-gate-pass` to `.gitignore` during implementation. It is runtime state, not source code.

## Sources

### Primary (HIGH confidence)
- `py_clob_client/exceptions.py` (source inspection) -- `PolyApiException` has `status_code` attribute for 401 detection
- `py_clob_client/http_helpers/helpers.py` (source inspection) -- `request()` raises `PolyApiException(resp)` on non-200 status
- `py_clob_client/client.py` (source inspection) -- `get_price()` is unauthenticated; `post_order()` calls `assert_level_2_auth()`; `create_or_derive_api_creds()` handles credential derivation
- `lib/trading.py` (codebase) -- current live trade execution pattern: fresh ClobClient per call
- `lib/config.py` (codebase) -- Config dataclass pattern with `_ENV_MAP` and `load_config()` factory
- `lib/db.py` (codebase) -- DataStore pattern with `get_strategy_stats()` for P&L data
- `tools/execute_trade.py` (codebase) -- existing CLI pattern with argparse, sys.path.insert, error_exit

### Secondary (MEDIUM confidence)
- macOS crontab behavior -- standard POSIX cron, verified available via `crontab -l`
- PID-file locking pattern -- standard Unix practice, `kill -0` for process existence check

### Tertiary (LOW confidence)
- Claude CLI exact flags for headless/cron execution -- needs empirical validation

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all verified installed
- Architecture: HIGH -- patterns are straightforward, locked decisions provide clear direction
- Pitfalls: HIGH -- key issues verified from source code inspection (flock unavailability, PolyApiException structure, get_price auth)
- Credential refresh: HIGH -- py-clob-client exception handling verified via source inspection
- Claude CLI cron flags: MEDIUM -- CLI is installed but exact headless flags need testing

**Research date:** 2026-03-27
**Valid until:** 2026-04-27 (stable domain -- cron, shell scripts, credential handling)
