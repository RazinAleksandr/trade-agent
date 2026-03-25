# Testing

## Running Tests

```bash
source .venv/bin/activate
python tests/test_paper_trading.py
```

Expected output:
```
✓ config OK
✓ data_store OK
✓ strategy_stats_empty OK
✓ pnl_from_resolved_positions OK
✓ market_discovery OK (3 markets)
✓ strategy OK
✓ portfolio OK
✓ trader paper mode OK

✓ All tests passed!
```

## Test Coverage

The test suite (`tests/test_paper_trading.py`) covers:

### `test_config`
Verifies `config.py` loads correctly:
- `PAPER_TRADING` is True
- `CHAIN_ID` is 137
- `KELLY_FRACTION` is positive

### `test_data_store`
Tests SQLite operations:
- Record a trade
- Upsert a position (create + update with averaging)
- Query open positions
- Calculate total exposure
- Close a position with realized P&L

### `test_strategy_stats_empty`
Verifies empty database returns correct defaults (0 trades, 0 win rate, 0 P&L).

### `test_pnl_from_resolved_positions`
End-to-end P&L test:
- Records a trade at entry price
- Closes position at known exit price
- Verifies realized P&L uses actual prices (not edge estimates)
- Checks win rate calculation

### `test_market_discovery`
**Hits the live Gamma API** — requires internet:
- Fetches 3 markets with minimal filters
- Validates `Market` dataclass fields are populated

### `test_strategy`
Tests Kelly criterion math:
- Positive edge (60% prob at 0.50 price) → positive Kelly
- No edge (50% prob at 0.50 price) → zero Kelly
- Negative edge (40% prob at 0.50 price) → zero Kelly (never bets against)

### `test_portfolio`
Verifies portfolio manager initializes and returns valid summaries:
- `get_portfolio_summary()` returns expected keys
- `check_risk_limits()` returns risk data

### `test_trader_paper`
Paper trade execution:
- Creates a `Trader` in paper mode
- Builds a `TradeSignal` and `Market`
- Executes signal
- Verifies success and paper order ID format

## Test Infrastructure

- Tests use a **temporary database** (`test_trading.db`) and log file (`test_trading.log`)
- Config is monkeypatched at the start: `config.DB_PATH = "test_trading.db"`
- Temp files are cleaned up after all tests pass
- `test_market_discovery` requires internet access (calls Gamma API)

## Adding New Tests

Tests follow a simple pattern — no framework required (plain `assert`):

```python
def test_my_feature():
    # Setup
    store = DataStore()

    # Act
    result = my_function()

    # Assert
    assert result.success, f"Expected success, got {result}"

    # Cleanup
    store.close()
    print("✓ my_feature OK")
```

Add your test function and call it from the `if __name__ == "__main__"` block at the bottom of the file.
