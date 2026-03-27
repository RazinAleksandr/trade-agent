"""JSON schema validation for sub-agent outputs.

Validates the structured JSON output from all 5 sub-agents:
Scanner, Analyst, Risk Manager, Planner, and Reviewer.

Uses plain Python dict checks (no jsonschema dependency).
Each validator returns (valid: bool, error_message: str).
"""


def _check_required_keys(
    data: dict, required: list[str], context: str
) -> tuple[bool, str]:
    """Check that all required keys exist in a dict."""
    for key in required:
        if key not in data:
            return False, f"Missing required field '{key}' in {context}"
    return True, ""


def _check_list_items(
    items: list, required_keys: list[str], context: str
) -> tuple[bool, str]:
    """Check that each item in a list has the required keys."""
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            return False, f"Item {i} in {context} is not a dict"
        for key in required_keys:
            if key not in item:
                return False, (
                    f"Item {i} in {context} missing required field '{key}'"
                )
    return True, ""


def validate_scanner_output(data: dict) -> tuple[bool, str]:
    """Validate scanner output JSON structure.

    Required fields: cycle_id (str), timestamp (str), markets_found (int),
    markets (list). Each market must have: id, question, yes_price, no_price,
    yes_token_id, no_token_id, neg_risk.
    """
    top_required = ["cycle_id", "timestamp", "markets_found", "markets"]
    valid, error = _check_required_keys(data, top_required, "scanner output")
    if not valid:
        return valid, error

    if not isinstance(data["markets"], list):
        return False, "Field 'markets' must be a list"

    market_required = [
        "id", "question", "yes_price", "no_price",
        "yes_token_id", "no_token_id", "neg_risk",
    ]
    return _check_list_items(data["markets"], market_required, "markets")


def validate_analyst_output(data: dict) -> tuple[bool, str]:
    """Validate analyst per-market output JSON structure.

    Required fields: cycle_id, market_id, question, timestamp,
    bull_case (with argument, evidence, probability_estimate),
    bear_case (with argument, evidence, probability_estimate),
    synthesis (with estimated_probability, confidence, reasoning,
    market_price, edge, recommended_side).
    """
    top_required = [
        "cycle_id", "market_id", "question", "timestamp",
        "bull_case", "bear_case", "synthesis",
    ]
    valid, error = _check_required_keys(data, top_required, "analyst output")
    if not valid:
        return valid, error

    # Validate bull_case
    bull_required = ["argument", "evidence", "probability_estimate"]
    valid, error = _check_required_keys(
        data["bull_case"], bull_required, "bull_case"
    )
    if not valid:
        return valid, error

    # Validate bear_case
    bear_required = ["argument", "evidence", "probability_estimate"]
    valid, error = _check_required_keys(
        data["bear_case"], bear_required, "bear_case"
    )
    if not valid:
        return valid, error

    # Validate synthesis
    synthesis_required = [
        "estimated_probability", "confidence", "reasoning",
        "market_price", "edge", "recommended_side",
    ]
    return _check_required_keys(
        data["synthesis"], synthesis_required, "synthesis"
    )


def validate_risk_output(data: dict) -> tuple[bool, str]:
    """Validate risk manager output JSON structure.

    Required fields: cycle_id, timestamp, portfolio_state (with total_exposure,
    remaining_capacity, num_open_positions), evaluated_markets (list, each with
    market_id, approved, position_size_usdc), rejected_markets (list).
    """
    top_required = [
        "cycle_id", "timestamp", "portfolio_state",
        "evaluated_markets", "rejected_markets",
    ]
    valid, error = _check_required_keys(data, top_required, "risk output")
    if not valid:
        return valid, error

    # Validate portfolio_state
    portfolio_required = [
        "total_exposure", "remaining_capacity", "num_open_positions",
    ]
    valid, error = _check_required_keys(
        data["portfolio_state"], portfolio_required, "portfolio_state"
    )
    if not valid:
        return valid, error

    if not isinstance(data["evaluated_markets"], list):
        return False, "Field 'evaluated_markets' must be a list"

    eval_required = ["market_id", "approved", "position_size_usdc"]
    return _check_list_items(
        data["evaluated_markets"], eval_required, "evaluated_markets"
    )


def validate_trade_plan(data: dict) -> tuple[bool, str]:
    """Validate planner trade plan JSON structure.

    Required fields: cycle_id, timestamp, strategy_context, trades (list,
    each with market_id, action, side, token_id, size, price, cost_usdc,
    reasoning), skipped_markets (list).
    """
    top_required = [
        "cycle_id", "timestamp", "strategy_context",
        "trades", "skipped_markets",
    ]
    valid, error = _check_required_keys(data, top_required, "trade plan")
    if not valid:
        return valid, error

    if not isinstance(data["trades"], list):
        return False, "Field 'trades' must be a list"

    trade_required = [
        "market_id", "action", "side", "token_id",
        "size", "price", "cost_usdc", "reasoning",
    ]
    return _check_list_items(data["trades"], trade_required, "trades")


def validate_reviewer_output(data: dict) -> tuple[bool, str]:
    """Validate reviewer output JSON structure.

    Required fields: cycle_id, timestamp, summary (with markets_scanned,
    markets_analyzed, trades_executed, trades_skipped, total_capital_deployed),
    trade_reviews (list), learnings (list), strategy_suggestions (list).
    """
    top_required = [
        "cycle_id", "timestamp", "summary",
        "trade_reviews", "learnings", "strategy_suggestions",
    ]
    valid, error = _check_required_keys(data, top_required, "reviewer output")
    if not valid:
        return valid, error

    # Validate summary
    summary_required = [
        "markets_scanned", "markets_analyzed", "trades_executed",
        "trades_skipped", "total_capital_deployed",
    ]
    return _check_required_keys(
        data["summary"], summary_required, "summary"
    )


def validate_strategy_update(data: dict) -> tuple[bool, str]:
    """Validate strategy update JSON structure.

    Required fields: cycle_id (str), timestamp (str),
    changes_applied (int), changes (list, each with domain, type, description),
    deferred (list), summary (str), git_committed (bool).
    """
    top_required = [
        "cycle_id", "timestamp", "changes_applied",
        "changes", "deferred", "summary", "git_committed",
    ]
    valid, error = _check_required_keys(data, top_required, "strategy update")
    if not valid:
        return valid, error

    if not isinstance(data["changes"], list):
        return False, "Field 'changes' must be a list"

    change_required = ["domain", "type", "description"]
    return _check_list_items(data["changes"], change_required, "changes")


def validate_position_monitor_output(data: dict) -> tuple[bool, str]:
    """Validate position monitor output JSON structure.

    Required fields: cycle_id (str), timestamp (str), positions_reviewed (int),
    recommendations (list). Each recommendation must have: market_id, action,
    sell_size, reasoning, urgency.
    """
    top_required = ["cycle_id", "timestamp", "positions_reviewed", "recommendations"]
    valid, error = _check_required_keys(data, top_required, "position monitor output")
    if not valid:
        return valid, error

    if not isinstance(data["recommendations"], list):
        return False, "Field 'recommendations' must be a list"

    rec_required = ["market_id", "action", "sell_size", "reasoning", "urgency"]
    return _check_list_items(
        data["recommendations"], rec_required, "recommendations"
    )


def validate_outcome_analysis(data: dict) -> tuple[bool, str]:
    """Validate outcome analyzer output JSON structure.

    Required fields: cycle_id (str), timestamp (str),
    positions_analyzed (int), analyses (list),
    calibration (dict), summary (str).
    Each analysis must have: market_id, estimated_prob, actual_outcome,
    brier_score, realized_pnl.
    """
    top_required = [
        "cycle_id", "timestamp", "positions_analyzed",
        "analyses", "calibration", "summary",
    ]
    valid, error = _check_required_keys(data, top_required, "outcome analysis")
    if not valid:
        return valid, error

    if not isinstance(data["analyses"], list):
        return False, "Field 'analyses' must be a list"

    analysis_required = [
        "market_id", "estimated_prob", "actual_outcome",
        "brier_score", "realized_pnl",
    ]
    return _check_list_items(data["analyses"], analysis_required, "analyses")
