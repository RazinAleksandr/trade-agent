#!/usr/bin/env bash
set -euo pipefail

# Run a single trading cycle inside a tmux session.
# Cron calls this script. If a cycle is already running, it skips.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCKFILE="/tmp/polymarket-cycle.pid"
# Read log file path set by schedule_trading.sh
if [ -f "$SCRIPT_DIR/.trading-logfile" ]; then
    LOGFILE=$(cat "$SCRIPT_DIR/.trading-logfile")
else
    LOGFILE="$SCRIPT_DIR/logs/manual-$(date +%Y%m%d-%H%M%S).log"
fi
SESSION_NAME="trading-$(date +%H%M%S)"
STOP_FILE="$SCRIPT_DIR/.trading-stop-at"
CRON_MARKER="# polymarket-trading-agent"

mkdir -p "$SCRIPT_DIR/logs"

log() { echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) $1" >> "$LOGFILE"; }

# Auto-stop: if past the scheduled end time, remove cron and exit
if [ -f "$STOP_FILE" ]; then
    STOP_EPOCH=$(cat "$STOP_FILE")
    if [ "$(date +%s)" -gt "$STOP_EPOCH" ]; then
        log "STOP: Trading duration expired, removing cron job"
        crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab - 2>/dev/null || true
        rm -f "$STOP_FILE"
        exit 0
    fi
fi

# Skip if a previous cycle is still running
if [ -f "$LOCKFILE" ]; then
    OLD_PID=$(cat "$LOCKFILE")
    if kill -0 "$OLD_PID" 2>/dev/null; then
        log "SKIP: Previous cycle still running (PID $OLD_PID)"
        exit 0
    else
        log "WARN: Stale lockfile removed (PID $OLD_PID)"
        rm -f "$LOCKFILE"
    fi
fi

# Write our PID
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

# Ensure PATH includes claude and common tools
if [ -f "$SCRIPT_DIR/.cron-env" ]; then
    source "$SCRIPT_DIR/.cron-env"
else
    export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.npm-global/bin:$HOME/.claude/local/bin:$PATH"
fi

log "START: session=$SESSION_NAME"

# Launch claude interactively in tmux
tmux new-session -d -s "$SESSION_NAME" \
    "cd $SCRIPT_DIR && source .venv/bin/activate && \
     unset CLAUDECODE && claude --dangerously-skip-permissions"

# Wait for claude to initialize, then send the prompt
sleep 5
tmux send-keys -t "$SESSION_NAME" "run a trading cycle" Enter

# Wait for claude to finish
while tmux has-session -t "$SESSION_NAME" 2>/dev/null; do
    if ! tmux list-panes -t "$SESSION_NAME" -F '#{pane_current_command}' 2>/dev/null | grep -q claude; then
        break
    fi
    sleep 30
done

log "END: session=$SESSION_NAME"
