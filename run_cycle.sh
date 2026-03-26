#!/usr/bin/env bash
set -euo pipefail

# Resolve project root from script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Constants
LOCKFILE="/tmp/polymarket-cycle.pid"
LOGDIR="$SCRIPT_DIR/logs"
LOGFILE="$LOGDIR/cron-$(date +%Y%m%d-%H%M%S).log"

# Ensure log directory exists
mkdir -p "$LOGDIR"

# PID-based lock check (macOS compatible; stale lock handling)
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

# Write PID and set cleanup trap
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Load PATH exported by setup_schedule.py at install time
ENVFILE="$SCRIPT_DIR/.cron-env"
if [ -f "$ENVFILE" ]; then
    source "$ENVFILE"
else
    # Fallback: add common tool locations
    export PATH="/usr/local/bin:/opt/homebrew/bin:$PATH"
fi

# Activate Python virtualenv
source "$SCRIPT_DIR/.venv/bin/activate"

# Change to project directory
cd "$SCRIPT_DIR"

# Run trading cycle via Claude CLI
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START: Trading cycle" >> "$LOGFILE"
claude --agent-file .claude/agents/trading-cycle.md \
    --print \
    --output-format text \
    --verbose \
    "Run a trading cycle" \
    >> "$LOGFILE" 2>&1
EXIT_CODE=$?
echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) END: Trading cycle (exit=$EXIT_CODE)" >> "$LOGFILE"
exit $EXIT_CODE
