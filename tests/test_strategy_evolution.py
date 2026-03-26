"""Tests for strategy evolution state files and contracts.

Validates that strategy.md follows the 4-domain structure,
core-principles.md is separate, and the strategy update
JSON schema is used correctly in integration contexts.
"""

import json
import os

import pytest


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_strategy_starts_blank():
    """strategy.md contains no pre-seeded rules -- only placeholder text (STRT-01)."""
    strategy_path = os.path.join(PROJECT_ROOT, "state", "strategy.md")
    assert os.path.isfile(strategy_path), "state/strategy.md does not exist"
    content = open(strategy_path).read()
    # Should contain placeholder markers, not actual rules
    assert "No rules yet" in content or "No approach defined" in content, (
        "strategy.md should contain placeholder text, not pre-seeded rules"
    )


def test_strategy_has_four_domains():
    """strategy.md contains all 4 required domain sections (STRT-03)."""
    strategy_path = os.path.join(PROJECT_ROOT, "state", "strategy.md")
    content = open(strategy_path).read()
    assert "## Market Selection Rules" in content
    assert "## Analysis Approach" in content
    assert "## Risk Parameters" in content
    assert "## Trade Entry/Exit Rules" in content


def test_strategy_has_no_core_principles_section():
    """strategy.md does NOT contain a Core Principles section (D-06)."""
    strategy_path = os.path.join(PROJECT_ROOT, "state", "strategy.md")
    content = open(strategy_path).read()
    assert "## Core Principles" not in content, (
        "Core Principles section must not be in strategy.md -- it lives in core-principles.md"
    )


def test_core_principles_separate():
    """core-principles.md exists as a separate file (STRT-04, D-06)."""
    principles_path = os.path.join(PROJECT_ROOT, "state", "core-principles.md")
    assert os.path.isfile(principles_path), "state/core-principles.md does not exist"
    content = open(principles_path).read()
    assert "never modified by the trading agent" in content.lower(), (
        "core-principles.md must state it is never modified by the agent"
    )


def test_core_principles_has_placeholder():
    """core-principles.md starts with placeholder for human operator (D-07)."""
    principles_path = os.path.join(PROJECT_ROOT, "state", "core-principles.md")
    content = open(principles_path).read()
    assert "to be defined" in content.lower(), (
        "core-principles.md should have placeholder text for human to fill in"
    )


def test_strategy_update_json_roundtrip(tmp_path):
    """A strategy_update.json file can be written and validated (STRT-02, STRT-06)."""
    from lib.agent_schemas import validate_strategy_update

    update_data = {
        "cycle_id": "20260326-150000",
        "timestamp": "2026-03-26T15:10:00Z",
        "reviewer_suggestions_count": 2,
        "changes_applied": 1,
        "changes_deferred": 1,
        "changes": [
            {
                "domain": "market_selection",
                "type": "new_rule",
                "description": "Focus on markets with >$5000 24h volume",
                "source_suggestion": "Reviewer suggestion #1",
            },
        ],
        "deferred": [
            {
                "suggestion": "Adjust Kelly fraction",
                "reason": "Need more data",
            },
        ],
        "summary": "Added volume filter rule.",
        "git_committed": True,
    }

    filepath = os.path.join(str(tmp_path), "strategy_update.json")
    with open(filepath, "w") as f:
        json.dump(update_data, f)

    with open(filepath) as f:
        loaded = json.load(f)

    valid, error = validate_strategy_update(loaded)
    assert valid, f"Strategy update validation failed: {error}"
