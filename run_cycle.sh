#!/usr/bin/env bash
set -euo pipefail

# Run a single trading cycle inside a tmux session.
# Cron calls this script. If a cycle is already running, it skips.
# The tmux session stays alive after completion so you can attach and inspect.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCKFILE="/tmp/polymarket-cycle.pid"
LOGDIR="$SCRIPT_DIR/logs"
LOGFILE="$LOGDIR/cron-$(date +%Y%m%d-%H%M%S).log"
SESSION_NAME="trading-$(date +%H%M%S)"

mkdir -p "$LOGDIR"

# Skip if a previous cycle is still running
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

# Ensure PATH includes claude and common tools
if [ -f "$SCRIPT_DIR/.cron-env" ]; then
    source "$SCRIPT_DIR/.cron-env"
else
    export PATH="/usr/local/bin:/opt/homebrew/bin:$HOME/.npm-global/bin:$HOME/.claude/local/bin:$PATH"
fi

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) START: Trading cycle in tmux session '$SESSION_NAME'" >> "$LOGFILE"

# Launch claude in a new tmux session with permissions bypassed.
# The session runs claude non-interactively with -p (print mode).
# After claude exits, the shell stays open so you can: tmux attach -t <session>
tmux new-session -d -s "$SESSION_NAME" \
    "cd $SCRIPT_DIR && source .venv/bin/activate && \
     claude -p 'run a trading cycle' --dangerously-skip-permissions \
     2>&1 | tee -a $LOGFILE; \
     echo ''; echo '=== Cycle finished at $(date) ==='; \
     echo 'Session: $SESSION_NAME — attach with: tmux attach -t $SESSION_NAME'; \
     exec bash"

# Wait for claude process to finish (poll tmux session)
while tmux has-session -t "$SESSION_NAME" 2>/dev/null; do
    # Check if claude is still running inside the session
    if ! tmux list-panes -t "$SESSION_NAME" -F '#{pane_current_command}' 2>/dev/null | grep -q claude; then
        break
    fi
    sleep 30
done

echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) END: Trading cycle" >> "$LOGFILE"
