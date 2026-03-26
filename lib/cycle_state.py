"""Cycle state management utilities.

Provides functions for:
- Generating timestamp-based cycle IDs
- Creating per-cycle directories in state/cycles/
- Retrieving recent cycle reports from state/reports/
"""

import os
from datetime import datetime, timezone


def generate_cycle_id() -> str:
    """Generate a timestamp-based cycle ID in format YYYYMMDD-HHMMSS."""
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d-%H%M%S")


def create_cycle_dir(base_path: str, cycle_id: str) -> str:
    """Create state/cycles/{cycle_id}/ directory.

    Args:
        base_path: Project root path.
        cycle_id: Timestamp-based cycle identifier.

    Returns:
        The absolute path to the created cycle directory.
    """
    cycle_dir = os.path.join(base_path, "state", "cycles", cycle_id)
    os.makedirs(cycle_dir, exist_ok=True)
    return cycle_dir


def get_recent_reports(base_path: str, count: int = 3) -> list[str]:
    """Return paths to the N most recent cycle reports, sorted newest first.

    Reports are markdown files in state/reports/ matching the pattern
    'cycle-*.md'. Sorted by filename descending (which, given the
    timestamp naming convention, means newest first).

    Args:
        base_path: Project root path.
        count: Maximum number of reports to return.

    Returns:
        List of absolute paths to the most recent report files.
    """
    reports_dir = os.path.join(base_path, "state", "reports")
    if not os.path.isdir(reports_dir):
        return []
    files = sorted(
        [
            f
            for f in os.listdir(reports_dir)
            if f.endswith(".md") and f.startswith("cycle-")
        ],
        reverse=True,
    )
    return [os.path.join(reports_dir, f) for f in files[:count]]
