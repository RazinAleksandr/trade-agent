"""Tests for cycle state management utilities.

Tests cycle ID generation, directory creation, JSON round-trip,
and recent report retrieval.
"""

import json
import os
import re

import pytest

from lib.cycle_state import create_cycle_dir, generate_cycle_id, get_recent_reports


def test_generate_cycle_id_format():
    """generate_cycle_id returns timestamp in YYYYMMDD-HHMMSS format."""
    cycle_id = generate_cycle_id()
    assert re.match(r"^\d{8}-\d{6}$", cycle_id), (
        f"Cycle ID '{cycle_id}' does not match YYYYMMDD-HHMMSS format"
    )


def test_create_cycle_dir(tmp_path):
    """create_cycle_dir creates state/cycles/{cycle_id}/ directory."""
    cycle_id = "20260326-143000"
    cycle_dir = create_cycle_dir(str(tmp_path), cycle_id)
    assert os.path.isdir(cycle_dir)
    assert cycle_dir == os.path.join(str(tmp_path), "state", "cycles", cycle_id)


def test_json_round_trip(tmp_path):
    """Write and read JSON round-trip through state/cycles/{cycle_id}/scanner_output.json."""
    cycle_id = "20260326-143000"
    cycle_dir = create_cycle_dir(str(tmp_path), cycle_id)

    data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T14:30:00Z",
        "markets_found": 3,
        "markets": [{"id": "m1", "question": "Test?"}],
    }

    output_path = os.path.join(cycle_dir, "scanner_output.json")
    with open(output_path, "w") as f:
        json.dump(data, f)

    with open(output_path) as f:
        loaded = json.load(f)

    assert loaded == data


def test_get_recent_reports(tmp_path):
    """get_recent_reports returns at most 3 most recent report files sorted by name descending."""
    reports_dir = os.path.join(str(tmp_path), "state", "reports")
    os.makedirs(reports_dir, exist_ok=True)

    # Create 5 report files with timestamped names
    for i, name in enumerate([
        "cycle-20260320-100000.md",
        "cycle-20260321-100000.md",
        "cycle-20260322-100000.md",
        "cycle-20260323-100000.md",
        "cycle-20260324-100000.md",
    ]):
        with open(os.path.join(reports_dir, name), "w") as f:
            f.write(f"# Cycle Report {i}")

    # Also create a non-matching file to ensure it's ignored
    with open(os.path.join(reports_dir, "notes.txt"), "w") as f:
        f.write("not a report")

    recent = get_recent_reports(str(tmp_path), count=3)
    assert len(recent) == 3
    # Should be sorted newest first
    assert "cycle-20260324-100000.md" in recent[0]
    assert "cycle-20260323-100000.md" in recent[1]
    assert "cycle-20260322-100000.md" in recent[2]
