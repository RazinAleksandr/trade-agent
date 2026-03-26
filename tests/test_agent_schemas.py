"""Tests for sub-agent JSON output schema validation.

Validates the structured JSON output schemas for all 5 sub-agents:
Scanner, Analyst, Risk Manager, Planner, and Reviewer.
"""

import pytest

from lib.agent_schemas import (
    validate_analyst_output,
    validate_reviewer_output,
    validate_risk_output,
    validate_scanner_output,
    validate_strategy_update,
    validate_trade_plan,
)


# --- Scanner Output Tests ---


def _valid_scanner_output():
    """Return a valid scanner output dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "timestamp": "2026-03-26T14:30:00Z",
        "markets_found": 2,
        "markets": [
            {
                "id": "market-abc-123",
                "question": "Will Bitcoin exceed $100,000 by June 2026?",
                "yes_price": 0.65,
                "no_price": 0.35,
                "yes_token_id": "token-yes-abc",
                "no_token_id": "token-no-abc",
                "neg_risk": False,
            },
            {
                "id": "market-xyz-456",
                "question": "Will ETH exceed $5,000?",
                "yes_price": 0.40,
                "no_price": 0.60,
                "yes_token_id": "token-yes-xyz",
                "no_token_id": "token-no-xyz",
                "neg_risk": True,
            },
        ],
    }


def test_validate_scanner_output_accepts_valid():
    """Scanner validation accepts valid output with all required fields."""
    data = _valid_scanner_output()
    valid, error = validate_scanner_output(data)
    assert valid, f"Expected valid, got error: {error}"


def test_validate_scanner_output_rejects_missing_markets():
    """Scanner validation rejects output missing the 'markets' field."""
    data = _valid_scanner_output()
    del data["markets"]
    valid, error = validate_scanner_output(data)
    assert not valid
    assert "markets" in error.lower()


def test_validate_scanner_output_rejects_market_missing_id():
    """Scanner validation rejects a market item missing the 'id' field."""
    data = _valid_scanner_output()
    del data["markets"][0]["id"]
    valid, error = validate_scanner_output(data)
    assert not valid
    assert "id" in error.lower()


# --- Analyst Output Tests ---


def _valid_analyst_output():
    """Return a valid analyst output dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "market_id": "market-abc-123",
        "question": "Will Bitcoin exceed $100,000 by June 2026?",
        "timestamp": "2026-03-26T14:32:15Z",
        "bull_case": {
            "argument": "Bitcoin ETF inflows accelerating",
            "evidence": ["source1", "source2"],
            "probability_estimate": 0.75,
        },
        "bear_case": {
            "argument": "Regulatory headwinds",
            "evidence": ["source3"],
            "probability_estimate": 0.55,
        },
        "synthesis": {
            "estimated_probability": 0.68,
            "confidence": 0.72,
            "reasoning": "Bull case stronger due to ETF flows",
            "market_price": 0.65,
            "edge": 0.03,
            "recommended_side": "YES",
        },
    }


def test_validate_analyst_output_accepts_valid():
    """Analyst validation accepts valid output with bull_case, bear_case, synthesis."""
    data = _valid_analyst_output()
    valid, error = validate_analyst_output(data)
    assert valid, f"Expected valid, got error: {error}"


def test_validate_analyst_output_rejects_missing_estimated_probability():
    """Analyst validation rejects output missing synthesis.estimated_probability."""
    data = _valid_analyst_output()
    del data["synthesis"]["estimated_probability"]
    valid, error = validate_analyst_output(data)
    assert not valid
    assert "estimated_probability" in error.lower()


# --- Risk Manager Output Tests ---


def _valid_risk_output():
    """Return a valid risk manager output dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "timestamp": "2026-03-26T14:35:00Z",
        "portfolio_state": {
            "total_exposure": 85.50,
            "remaining_capacity": 114.50,
            "num_open_positions": 3,
        },
        "evaluated_markets": [
            {
                "market_id": "market-abc-123",
                "approved": True,
                "position_size_usdc": 12.50,
            },
        ],
        "rejected_markets": [],
    }


def test_validate_risk_output_accepts_valid():
    """Risk validation accepts valid output with portfolio_state and evaluated_markets."""
    data = _valid_risk_output()
    valid, error = validate_risk_output(data)
    assert valid, f"Expected valid, got error: {error}"


def test_validate_risk_output_rejects_missing_approved():
    """Risk validation rejects an evaluated_market missing the 'approved' field."""
    data = _valid_risk_output()
    del data["evaluated_markets"][0]["approved"]
    valid, error = validate_risk_output(data)
    assert not valid
    assert "approved" in error.lower()


# --- Trade Plan Tests ---


def _valid_trade_plan():
    """Return a valid trade plan dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "timestamp": "2026-03-26T14:37:00Z",
        "strategy_context": "Conservative positioning",
        "trades": [
            {
                "market_id": "market-abc-123",
                "action": "BUY",
                "side": "YES",
                "token_id": "token-yes-abc",
                "size": 19.23,
                "price": 0.65,
                "cost_usdc": 12.50,
                "reasoning": "Strong ETF inflows",
            },
        ],
        "skipped_markets": [],
    }


def test_validate_trade_plan_accepts_valid():
    """Trade plan validation accepts valid output with trades array."""
    data = _valid_trade_plan()
    valid, error = validate_trade_plan(data)
    assert valid, f"Expected valid, got error: {error}"


# --- Reviewer Output Tests ---


def _valid_reviewer_output():
    """Return a valid reviewer output dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "timestamp": "2026-03-26T14:45:00Z",
        "summary": {
            "markets_scanned": 7,
            "markets_analyzed": 6,
            "trades_executed": 2,
            "trades_skipped": 4,
            "total_capital_deployed": 25.00,
        },
        "trade_reviews": [],
        "learnings": ["Crypto edges are thin"],
        "strategy_suggestions": ["Increase MIN_EDGE_THRESHOLD"],
    }


def test_validate_reviewer_output_accepts_valid():
    """Reviewer validation accepts valid output with summary and learnings."""
    data = _valid_reviewer_output()
    valid, error = validate_reviewer_output(data)
    assert valid, f"Expected valid, got error: {error}"


def test_validate_reviewer_output_rejects_missing_markets_scanned():
    """Reviewer validation rejects output missing summary.markets_scanned."""
    data = _valid_reviewer_output()
    del data["summary"]["markets_scanned"]
    valid, error = validate_reviewer_output(data)
    assert not valid
    assert "markets_scanned" in error.lower()


# --- Strategy Update Tests ---


def _valid_strategy_update():
    """Return a valid strategy update dict for testing."""
    return {
        "cycle_id": "20260326-143000",
        "timestamp": "2026-03-26T14:50:00Z",
        "reviewer_suggestions_count": 3,
        "changes_applied": 2,
        "changes_deferred": 1,
        "changes": [
            {
                "domain": "market_selection",
                "type": "new_rule",
                "description": "Prioritize markets with 7-30 day expiry",
                "source_suggestion": "Reviewer suggestion #1",
            },
            {
                "domain": "risk_parameters",
                "type": "refinement",
                "description": "Lower sizing for markets with < 0.6 confidence",
                "source_suggestion": "Reviewer suggestion #2",
            },
        ],
        "deferred": [
            {
                "suggestion": "Increase MIN_EDGE_THRESHOLD to 0.12",
                "reason": "Insufficient data after 1 cycle",
            },
        ],
        "summary": "Added market expiry rule and refined sizing guidance.",
        "git_committed": True,
    }


def test_validate_strategy_update_accepts_valid():
    """Strategy update validation accepts valid output with changes and deferred."""
    data = _valid_strategy_update()
    valid, error = validate_strategy_update(data)
    assert valid, f"Expected valid, got error: {error}"


def test_validate_strategy_update_rejects_missing_changes():
    """Strategy update validation rejects output missing the 'changes' field."""
    data = _valid_strategy_update()
    del data["changes"]
    valid, error = validate_strategy_update(data)
    assert not valid
    assert "changes" in error.lower()


def test_validate_strategy_update_rejects_change_missing_domain():
    """Strategy update validation rejects a change item missing 'domain'."""
    data = _valid_strategy_update()
    del data["changes"][0]["domain"]
    valid, error = validate_strategy_update(data)
    assert not valid
    assert "domain" in error.lower()


def test_validate_strategy_update_accepts_empty_changes():
    """Strategy update validation accepts output with empty changes list (no-op cycle)."""
    data = _valid_strategy_update()
    data["changes"] = []
    data["changes_applied"] = 0
    valid, error = validate_strategy_update(data)
    assert valid, f"Expected valid, got error: {error}"
