#!/usr/bin/env bash
set -euo pipefail

# Schedule autonomous trading cycles via cron.
#
# Usage:
#   ./schedule_trading.sh start --every 4h --for 7d    # Run every 4 hours for 7 days
#   ./schedule_trading.sh start --every 6h --for 3d    # Run every 6 hours for 3 days
#   ./schedule_trading.sh start --every 2h --for 1d    # Run every 2 hours for 1 day
#   ./schedule_trading.sh stop                          # Remove the cron job immediately
#   ./schedule_trading.sh status                        # Check if trading is scheduled
#
# Each cycle runs in its own tmux session. You can attach to watch:
#   tmux ls                          # List sessions
#   tmux attach -t trading-HHMMSS    # Attach to a session
#
# Logs are written to ./logs/cron-*.log

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_MARKER="# polymarket-trading-agent"
STOP_FILE="$SCRIPT_DIR/.trading-stop-at"

usage() {
    echo "Usage:"
    echo "  $0 start --every <frequency> --for <duration>"
    echo "  $0 stop"
    echo "  $0 status"
    echo ""
    echo "Frequency: 1h, 2h, 4h, 6h, 8h, 12h"
    echo "Duration:  hours (e.g. 12h) or days (e.g. 7d)"
    echo ""
    echo "Examples:"
    echo "  $0 start --every 4h --for 7d"
    echo "  $0 start --every 6h --for 3d"
    exit 1
}

parse_hours() {
    local val="$1"
    case "$val" in
        1h)  echo 1 ;;
        2h)  echo 2 ;;
        4h)  echo 4 ;;
        6h)  echo 6 ;;
        8h)  echo 8 ;;
        12h) echo 12 ;;
        *)   echo "Error: Unsupported frequency '$val'. Use: 1h, 2h, 4h, 6h, 8h, 12h" >&2; exit 1 ;;
    esac
}

parse_duration_seconds() {
    local val="$1"
    case "$val" in
        [0-9]*h) echo $(( ${val%h} * 3600 )) ;;
        [0-9]*d) echo $(( ${val%d} * 86400 )) ;;
        *)       echo "Error: Unsupported duration '$val'. Use hours (e.g. 12h) or days (e.g. 7d)" >&2; exit 1 ;;
    esac
}

do_start() {
    local freq=""
    local dur=""

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --every) freq="$2"; shift 2 ;;
            --for)   dur="$2"; shift 2 ;;
            *)       usage ;;
        esac
    done

    if [[ -z "$freq" || -z "$dur" ]]; then
        usage
    fi

    local hours
    hours=$(parse_hours "$freq")
    local dur_secs
    dur_secs=$(parse_duration_seconds "$dur")

    # Calculate stop date
    local stop_epoch stop_date
    stop_epoch=$(( $(date +%s) + dur_secs ))
    if [[ "$(uname)" == "Darwin" ]]; then
        stop_date=$(date -r "$stop_epoch" +%Y-%m-%dT%H:%M:%S)
    else
        stop_date=$(date -d "@$stop_epoch" +%Y-%m-%dT%H:%M:%S)
    fi

    # Save stop time and create session log file
    echo "$stop_epoch" > "$STOP_FILE"
    local session_log="$SCRIPT_DIR/logs/session-$(date +%Y%m%d-%H%M%S).log"
    mkdir -p "$SCRIPT_DIR/logs"
    echo "$session_log" > "$SCRIPT_DIR/.trading-logfile"
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) SESSION: every $freq for $dur (until $stop_date)" > "$session_log"

    # Remove any existing polymarket cron entry
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab - 2>/dev/null || true

    # Build cron schedule: every N hours
    local cron_schedule
    if [[ "$hours" -eq 1 ]]; then
        cron_schedule="0 * * * *"
    else
        cron_schedule="0 */${hours} * * *"
    fi

    # Simple cron line — auto-stop logic is in run_cycle.sh
    local cron_line="$cron_schedule $SCRIPT_DIR/run_cycle.sh $CRON_MARKER"

    # Install cron job
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER" || true; echo "$cron_line") | crontab -

    echo "Trading scheduled:"
    echo "  Frequency: every $freq"
    echo "  Duration:  $dur (until $stop_date)"
    echo "  Stop file: $STOP_FILE"
    echo ""
    echo "The agent will run every ${hours}h and auto-stop after $dur."
    echo "Watch sessions: tmux ls"
    echo "Check logs:     ls -la $SCRIPT_DIR/logs/"
    echo "Stop early:     $0 stop"
    echo ""

    # Run first cycle immediately
    echo "Starting first cycle now..."
    "$SCRIPT_DIR/run_cycle.sh" &
}

do_stop() {
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab - 2>/dev/null || true
    rm -f "$STOP_FILE" "$SCRIPT_DIR/.trading-logfile"
    echo "Trading schedule removed."
    echo ""
    echo "Note: any currently running cycle will finish. Check with: tmux ls"
}

do_status() {
    echo "=== Cron Job ==="
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        crontab -l 2>/dev/null | grep "$CRON_MARKER"
        if [ -f "$STOP_FILE" ]; then
            local stop_epoch
            stop_epoch=$(cat "$STOP_FILE")
            if [[ "$(uname)" == "Darwin" ]]; then
                local stop_date
                stop_date=$(date -r "$stop_epoch" +%Y-%m-%dT%H:%M:%S)
            else
                local stop_date
                stop_date=$(date -d "@$stop_epoch" +%Y-%m-%dT%H:%M:%S)
            fi
            echo "Auto-stops at: $stop_date"
        fi
    else
        echo "No trading schedule active."
    fi

    echo ""
    echo "=== Active tmux Sessions ==="
    tmux ls 2>/dev/null | grep trading || echo "No trading sessions running."

    echo ""
    echo "=== Recent Logs ==="
    ls -lt "$SCRIPT_DIR/logs/" 2>/dev/null | head -5 || echo "No logs yet."
}

# Main
case "${1:-}" in
    start)  shift; do_start "$@" ;;
    stop)   do_stop ;;
    status) do_status ;;
    *)      usage ;;
esac
