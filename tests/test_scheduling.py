"""Tests for tools/setup_schedule.py -- interval parsing and crontab management."""

import os
import sys

import pytest

# Make tools/ importable
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"))

from setup_schedule import interval_to_cron, CRON_MARKER


class TestIntervalToCron:
    """Test CYCLE_INTERVAL -> cron expression conversion."""

    def test_30_minutes(self):
        assert interval_to_cron("30m") == "*/30 * * * *"

    def test_1_hour(self):
        assert interval_to_cron("1h") == "0 * * * *"

    def test_2_hours(self):
        assert interval_to_cron("2h") == "0 */2 * * *"

    def test_4_hours(self):
        assert interval_to_cron("4h") == "0 */4 * * *"

    def test_6_hours(self):
        assert interval_to_cron("6h") == "0 */6 * * *"

    def test_12_hours(self):
        assert interval_to_cron("12h") == "0 */12 * * *"

    def test_1_day(self):
        assert interval_to_cron("1d") == "0 0 * * *"

    def test_15_minutes(self):
        assert interval_to_cron("15m") == "*/15 * * * *"

    def test_invalid_format(self):
        with pytest.raises(ValueError, match="Invalid interval"):
            interval_to_cron("abc")

    def test_zero_minutes(self):
        with pytest.raises(ValueError, match="Minutes must be 1-59"):
            interval_to_cron("0m")

    def test_60_minutes(self):
        with pytest.raises(ValueError, match="Minutes must be 1-59"):
            interval_to_cron("60m")

    def test_24_hours(self):
        with pytest.raises(ValueError, match="Hours must be 1-23"):
            interval_to_cron("24h")

    def test_2_days(self):
        with pytest.raises(ValueError, match="Only '1d'"):
            interval_to_cron("2d")

    def test_whitespace_stripped(self):
        assert interval_to_cron("  4h  ") == "0 */4 * * *"

    def test_uppercase(self):
        assert interval_to_cron("4H") == "0 */4 * * *"


class TestCrontabManagement:
    """Test crontab entry building and filtering."""

    def test_cron_marker_defined(self):
        assert "polymarket" in CRON_MARKER.lower()

    def test_filter_preserves_other_entries(self):
        """Existing non-polymarket crontab entries are preserved."""
        lines = [
            "0 * * * * /usr/bin/backup.sh",
            f"0 */4 * * * /path/to/run_cycle.sh {CRON_MARKER}",
            "30 2 * * * /usr/bin/cleanup.sh",
        ]
        filtered = [l for l in lines if CRON_MARKER not in l]
        assert len(filtered) == 2
        assert "/usr/bin/backup.sh" in filtered[0]
        assert "/usr/bin/cleanup.sh" in filtered[1]
