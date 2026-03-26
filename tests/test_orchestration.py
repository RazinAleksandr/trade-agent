"""Tests for orchestration utilities and integration points.

Validates the execution_results JSON schema, cycle report naming convention,
and verifies a complete cycle directory contains all expected files that
pass their respective schema validations.
"""

import json
import os
import re

import pytest

from lib.agent_schemas import (
    validate_analyst_output,
    validate_reviewer_output,
    validate_risk_output,
    validate_scanner_output,
    validate_trade_plan,
)
from lib.cycle_state import create_cycle_dir, generate_cycle_id


def validate_execution_results(data: dict) -> tuple[bool, str]:
    """Validate execution_results JSON structure.

    Required fields: cycle_id, timestamp, trades_attempted, trades_succeeded,
    trades_failed, results (list). Each result item must have:
    market_id, side, size, price, success.
    """
    top_required = [
        "cycle_id", "timestamp", "trades_attempted",
        "trades_succeeded", "trades_failed", "results",
    ]
    for key in top_required:
        if key not in data:
            return False, f"Missing required field '{key}' in execution_results"

    if not isinstance(data["results"], list):
        return False, "Field 'results' must be a list"

    result_required = ["market_id", "side", "size", "price", "success"]
    for i, item in enumerate(data["results"]):
        if not isinstance(item, dict):
            return False, f"Item {i} in results is not a dict"
        for key in result_required:
            if key not in item:
                return False, (
                    f"Item {i} in results missing required field '{key}'"
                )

    return True, ""


# --- Test 1: Execution results valid round-trip ---


def test_execution_results_valid():
    """Create a valid execution results dict with 2 results (1 success, 1 failure),
    call validate_execution_results, assert True."""
    data = {
        "cycle_id": "20260326-150000",
        "timestamp": "2026-03-26T15:00:00Z",
        "trades_attempted": 2,
        "trades_succeeded": 1,
        "trades_failed": 1,
        "results": [
            {
                "market_id": "market-abc-123",
                "side": "YES",
                "size": 19.23,
                "price": 0.65,
                "order_id": "paper-abc123",
                "success": True,
                "message": "Paper trade recorded",
                "is_paper": True,
            },
            {
                "market_id": "market-xyz-456",
                "side": "NO",
                "size": 10.0,
                "price": 0.40,
                "order_id": None,
                "success": False,
                "message": "Execution failed: price unavailable",
                "is_paper": True,
            },
        ],
    }
    valid, error = validate_execution_results(data)
    assert valid, f"Expected valid, got error: {error}"


# --- Test 2: Execution results missing 'results' field ---


def test_execution_results_missing_results():
    """Create dict without 'results' key, assert validation fails
    with 'results' in error message."""
    data = {
        "cycle_id": "20260326-150000",
        "timestamp": "2026-03-26T15:00:00Z",
        "trades_attempted": 0,
        "trades_succeeded": 0,
        "trades_failed": 0,
    }
    valid, error = validate_execution_results(data)
    assert not valid
    assert "results" in error.lower()


# --- Test 3: Cycle report naming follows pattern ---


def test_cycle_report_naming():
    """Call generate_cycle_id(), form filename as cycle-{id}.md,
    assert regex match for cycle-YYYYMMDD-HHMMSS.md."""
    cycle_id = generate_cycle_id()
    filename = f"cycle-{cycle_id}.md"
    assert re.match(r"^cycle-\d{8}-\d{6}\.md$", filename), (
        f"Filename '{filename}' does not match cycle-YYYYMMDD-HHMMSS.md pattern"
    )


# --- Test 4: Full pipeline file set ---


def test_full_pipeline_file_set(tmp_path):
    """Create a cycle dir with all 6 expected JSON files, verify all exist
    and pass their respective schema validations."""
    cycle_id = "20260326-150000"
    cycle_dir = create_cycle_dir(str(tmp_path), cycle_id)

    # 1. Scanner output
    scanner_data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T15:00:00Z",
        "markets_found": 1,
        "markets": [
            {
                "id": "m1",
                "question": "Test market?",
                "yes_price": 0.60,
                "no_price": 0.40,
                "yes_token_id": "tok-yes-1",
                "no_token_id": "tok-no-1",
                "neg_risk": False,
            },
        ],
    }
    with open(os.path.join(cycle_dir, "scanner_output.json"), "w") as f:
        json.dump(scanner_data, f)

    # 2. Analyst output (per market)
    analyst_data = {
        "cycle_id": cycle_id,
        "market_id": "m1",
        "question": "Test market?",
        "timestamp": "2026-03-26T15:01:00Z",
        "bull_case": {
            "argument": "Strong evidence for YES",
            "evidence": ["source1"],
            "probability_estimate": 0.75,
        },
        "bear_case": {
            "argument": "Some counter-evidence",
            "evidence": ["source2"],
            "probability_estimate": 0.50,
        },
        "synthesis": {
            "estimated_probability": 0.65,
            "confidence": 0.70,
            "reasoning": "Bull case slightly stronger",
            "market_price": 0.60,
            "edge": 0.05,
            "recommended_side": "YES",
        },
    }
    with open(os.path.join(cycle_dir, "analyst_m1.json"), "w") as f:
        json.dump(analyst_data, f)

    # 3. Risk output
    risk_data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T15:02:00Z",
        "portfolio_state": {
            "total_exposure": 50.0,
            "remaining_capacity": 150.0,
            "num_open_positions": 1,
        },
        "evaluated_markets": [
            {
                "market_id": "m1",
                "approved": True,
                "position_size_usdc": 10.0,
            },
        ],
        "rejected_markets": [],
    }
    with open(os.path.join(cycle_dir, "risk_output.json"), "w") as f:
        json.dump(risk_data, f)

    # 4. Trade plan
    trade_plan_data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T15:03:00Z",
        "strategy_context": "Default strategy -- no rules yet",
        "trades": [
            {
                "market_id": "m1",
                "action": "BUY",
                "side": "YES",
                "token_id": "tok-yes-1",
                "size": 15.38,
                "price": 0.65,
                "cost_usdc": 10.0,
                "reasoning": "Positive edge with moderate confidence",
            },
        ],
        "skipped_markets": [],
    }
    with open(os.path.join(cycle_dir, "trade_plan.json"), "w") as f:
        json.dump(trade_plan_data, f)

    # 5. Execution results
    execution_data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T15:04:00Z",
        "trades_attempted": 1,
        "trades_succeeded": 1,
        "trades_failed": 0,
        "results": [
            {
                "market_id": "m1",
                "side": "YES",
                "size": 15.38,
                "price": 0.65,
                "order_id": "paper-001",
                "success": True,
                "message": "Paper trade recorded",
                "is_paper": True,
            },
        ],
    }
    with open(os.path.join(cycle_dir, "execution_results.json"), "w") as f:
        json.dump(execution_data, f)

    # 6. Reviewer output
    reviewer_data = {
        "cycle_id": cycle_id,
        "timestamp": "2026-03-26T15:05:00Z",
        "summary": {
            "markets_scanned": 1,
            "markets_analyzed": 1,
            "trades_executed": 1,
            "trades_skipped": 0,
            "total_capital_deployed": 10.0,
        },
        "trade_reviews": [],
        "learnings": ["First cycle completed successfully"],
        "strategy_suggestions": ["Monitor edge accuracy over time"],
    }
    with open(os.path.join(cycle_dir, "reviewer_output.json"), "w") as f:
        json.dump(reviewer_data, f)

    # Verify all 6 files exist
    expected_files = [
        "scanner_output.json",
        "analyst_m1.json",
        "risk_output.json",
        "trade_plan.json",
        "execution_results.json",
        "reviewer_output.json",
    ]
    for filename in expected_files:
        filepath = os.path.join(cycle_dir, filename)
        assert os.path.isfile(filepath), f"Missing file: {filename}"

    # Verify each passes its respective schema validation
    with open(os.path.join(cycle_dir, "scanner_output.json")) as f:
        valid, error = validate_scanner_output(json.load(f))
        assert valid, f"Scanner validation failed: {error}"

    with open(os.path.join(cycle_dir, "analyst_m1.json")) as f:
        valid, error = validate_analyst_output(json.load(f))
        assert valid, f"Analyst validation failed: {error}"

    with open(os.path.join(cycle_dir, "risk_output.json")) as f:
        valid, error = validate_risk_output(json.load(f))
        assert valid, f"Risk validation failed: {error}"

    with open(os.path.join(cycle_dir, "trade_plan.json")) as f:
        valid, error = validate_trade_plan(json.load(f))
        assert valid, f"Trade plan validation failed: {error}"

    with open(os.path.join(cycle_dir, "execution_results.json")) as f:
        valid, error = validate_execution_results(json.load(f))
        assert valid, f"Execution results validation failed: {error}"

    with open(os.path.join(cycle_dir, "reviewer_output.json")) as f:
        valid, error = validate_reviewer_output(json.load(f))
        assert valid, f"Reviewer validation failed: {error}"
