"""Tests for CLI tools -- argument parsing, output format, signal handling."""

import json
import os
import signal
import subprocess
import sys

import pytest

from lib.models import Market


# Resolve paths relative to the project root (worktree)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DISCOVER_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "discover_markets.py")
GET_PRICES_SCRIPT = os.path.join(PROJECT_ROOT, "tools", "get_prices.py")


def _run_tool(script_path, args=None, timeout=10):
    """Run a CLI tool as a subprocess and return the result."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=PROJECT_ROOT,
    )


# --- discover_markets.py ---

def test_discover_markets_help():
    """--help exits 0 and shows description."""
    result = _run_tool(DISCOVER_SCRIPT, ["--help"])
    assert result.returncode == 0
    assert "Discover active Polymarket markets" in result.stdout


def test_discover_markets_invalid_arg():
    """Invalid flag produces non-zero exit code."""
    result = _run_tool(DISCOVER_SCRIPT, ["--invalid-flag"])
    assert result.returncode != 0


def test_discover_markets_json_output():
    """discover_markets outputs valid JSON array to stdout with expected keys."""
    # Use PROJECT_ROOT directly since -c mode has no __file__
    mock_code = f'''
import sys, json, os
sys.path.insert(0, "{PROJECT_ROOT}")

from unittest.mock import patch
from lib.models import Market

fake_markets = [
    Market(
        id="1", condition_id="0xabc", question="Will it rain?",
        description="Weather", yes_token_id="tok1", no_token_id="tok2",
        yes_price=0.6, no_price=0.4, best_bid=0.58, best_ask=0.62,
        volume_24h=5000.0, liquidity=2000.0, end_date="2026-12-31",
        category="Weather", active=True, closed=False,
        neg_risk=False, order_min_size=5.0, tick_size=0.01
    ),
    Market(
        id="2", condition_id="0xdef", question="Will BTC hit 100k?",
        description="Crypto", yes_token_id="tok3", no_token_id="tok4",
        yes_price=0.45, no_price=0.55, best_bid=0.43, best_ask=0.47,
        volume_24h=80000.0, liquidity=30000.0, end_date="2026-06-30",
        category="Crypto", active=True, closed=False,
        neg_risk=True, order_min_size=5.0, tick_size=0.01
    ),
]

with patch("lib.market_data.fetch_active_markets", return_value=fake_markets):
    from tools.discover_markets import main
    main()
'''
    result = subprocess.run(
        [sys.executable, "-c", mock_code],
        capture_output=True,
        text=True,
        timeout=10,
        cwd=PROJECT_ROOT,
    )

    assert result.returncode == 0, f"stderr: {result.stderr}"
    data = json.loads(result.stdout)
    assert isinstance(data, list)
    assert len(data) == 2
    # Verify expected keys
    for item in data:
        assert "id" in item
        assert "question" in item
        assert "neg_risk" in item
        assert "best_bid" in item
        assert "best_ask" in item


# --- get_prices.py ---

def test_get_prices_help():
    """--help exits 0 and shows --token-id."""
    result = _run_tool(GET_PRICES_SCRIPT, ["--help"])
    assert result.returncode == 0
    assert "--token-id" in result.stdout


def test_get_prices_missing_required():
    """Missing --token-id produces non-zero exit code."""
    result = _run_tool(GET_PRICES_SCRIPT)
    assert result.returncode != 0


# --- Signal handling ---

def test_sigint_handling():
    """register_shutdown_handler sets flag on SIGINT."""
    from lib.signals import register_shutdown_handler, is_shutdown_requested, _signal_handler

    # Directly invoke the signal handler function (simulates SIGINT)
    import lib.signals
    lib.signals._shutdown_requested = False  # reset state
    assert is_shutdown_requested() is False

    register_shutdown_handler()
    _signal_handler(signal.SIGINT, None)
    assert is_shutdown_requested() is True

    # Reset for other tests
    lib.signals._shutdown_requested = False
