# Testing Patterns

**Analysis Date:** 2026-03-25

## Test Framework

**Runner:**
- Python's standard unittest framework (no pytest installed)
- Tests are simple functions with assertions, executed directly

**Config:** Tests override `DB_PATH`, `LOG_FILE`, and `PAPER_TRADING` before importing modules
```python
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
os.environ["PAPER_TRADING"] = "true"
os.environ["LOG_FILE"] = tempfile.mktemp(suffix=".log")
```

**Run command:**
```bash
python tests/test_paper_trading.py
```

**Assertion library:**
- Built-in Python `assert` statements with comparison operators
- No pytest, unittest.TestCase, or external assertion libraries

## Test File Organization

**Location:**
- Single test file: `tests/test_paper_trading.py`
- Tests import modules from parent directory via `sys.path.insert()`

**Naming:**
- Functions prefixed with `test_`: `test_config()`, `test_data_store()`, `test_trader_paper()`
- No test class wrapping (flat function structure)

**Structure:**
```
tests/
└── test_paper_trading.py
    ├── test_config()
    ├── test_data_store()
    ├── test_market_discovery()
    ├── test_strategy()
    ├── test_portfolio()
    ├── test_strategy_stats_empty()
    ├── test_pnl_from_resolved_positions()
    ├── test_trader_paper()
    └── if __name__ == "__main__":
            [run all tests sequentially]
```

## Test Structure

**Setup pattern:** Tests initialize components directly
```python
def test_data_store():
    from data_store import DataStore
    store = DataStore()

    # Test operations
    trade_id = store.record_trade(...)

    # Assertions
    assert trade_id > 0
    store.close()
```

**Teardown pattern:** Explicit `.close()` calls
```python
store.close()  # closes SQLite connection
print("✓ data_store OK")
```

**No setup/teardown functions:** Each test is self-contained with local initialization

**Isolation:** Each test uses a temporary database via `tempfile.mktemp(suffix=".db")`
```python
os.environ["DB_PATH"] = tempfile.mktemp(suffix=".db")
store = DataStore(db_path=tempfile.mktemp(suffix=".db"))
```

## Mocking

**Approach:** Minimal mocking — tests prefer real component integration

**Live API calls:** `test_market_discovery()` calls actual Gamma API
```python
def test_market_discovery():
    from market_discovery import fetch_active_markets
    markets = fetch_active_markets(limit=3, min_volume=100, min_liquidity=50)
    assert len(markets) > 0
```

**No external mocking:** OpenAI API not tested; market analysis tests don't exist

**Data objects created inline:** For unit tests, construct test dataclasses directly
```python
market = Market(
    id="test-456",
    condition_id="cond-456",
    question="Test market?",
    yes_token_id="token-yes-456",
    # ... all fields provided
)
```

## Fixtures and Factories

**Test data pattern:** Inline dataclass construction for each test

**Example from `test_trader_paper()`:**
```python
signal = TradeSignal(
    market_id="test-456",
    question="Test market?",
    side="YES",
    token_id="",
    price=0.60,
    size=5.0,
    cost_usdc=3.0,
    edge=0.10,
    kelly_raw=0.20,
    kelly_adjusted=0.05,
    confidence=0.7,
    reasoning="Test trade",
)
```

**No factory functions or fixtures defined** — each test manually constructs needed objects

**No shared fixtures:** No conftest.py or shared setup

## Coverage

**Requirements:** Not enforced; no coverage configuration found

**What's tested:**
- Core workflows: config, data persistence, strategy calculations, paper trading
- Error paths: graceful degradation (e.g., empty stats on no trades)
- Integration: full stack (market discovery, trader, portfolio)

**What's NOT tested:**
- Live trading (code exists but not tested)
- Market analyzer (requires OpenAI API)
- Wallet setup (requires blockchain interaction)
- Portfolio risk checks (called but assertions minimal)
- Logging correctness (just calls functions)

## Test Types

**Integration tests** (majority of tests):
- Scope: Full module functionality with real databases
- Approach: Create components, exercise workflows, verify state changes
- Example: `test_data_store()` records trades, opens/closes positions, checks stats
- No mocks; real SQLite DB (in temp file)

**Unit tests** (Kelly criterion only):
```python
def test_strategy():
    from strategy import kelly_criterion, TradeSignal

    # Kelly: 60% chance, buying at 0.50
    k = kelly_criterion(0.60, 0.50, fraction=1.0)
    assert k > 0

    # Kelly: no edge (50% at 0.50)
    k = kelly_criterion(0.50, 0.50, fraction=1.0)
    assert k == 0

    # Kelly: negative edge
    k = kelly_criterion(0.40, 0.50, fraction=1.0)
    assert k == 0
```

**E2E tests:** Not present — no browser or end-to-end orchestration tests

## Common Patterns

**Assertions used:**
- `assert condition` — simple boolean check
- `assert value == expected` — equality
- `assert len(collection) == count` — collection size
- `assert dict_key in dict` — key presence
- `assert 0 < value < 1` — range checks
- `assert abs(a - b) < tolerance` — float comparison with epsilon
  ```python
  assert abs(stats["total_pnl"] - 3.0) < 1e-6, f"Expected ~3.0, got {stats['total_pnl']}"
  ```

**Error assertion pattern:**
```python
k = kelly_criterion(0.50, 0.50, fraction=1.0)
assert k == 0, f"Expected zero Kelly, got {k}"
```

**Multi-step test pattern:**
```python
# Step 1: Record data
trade_id = store.record_trade(...)
assert trade_id > 0

# Step 2: Fetch data
positions = store.get_open_positions()
assert len(positions) == 1

# Step 3: Mutate
store.close_position("test-123", exit_price=0.75)

# Step 4: Verify final state
positions = store.get_open_positions()
assert len(positions) == 0
```

**P&L verification with tolerance:**
```python
def test_pnl_from_resolved_positions():
    # ... setup ...
    store.close_position("pnl-test-001", exit_price=0.80)
    stats = store.get_strategy_stats()

    # Realized PnL = (0.80 - 0.50) * 10 = 3.0
    assert abs(stats["total_pnl"] - 3.0) < 1e-6, \
        f"Expected ~3.0, got {stats['total_pnl']}"
    assert stats["win_rate"] == 1.0
```

**Test output verbosity:**
```python
print(f"✓ market_discovery OK ({len(markets)} markets)")
print("\n✓ All tests passed!")
```

## Running Tests

**Manual execution:**
```bash
python tests/test_paper_trading.py
```

**Output:**
```
✓ config OK
✓ data_store OK
✓ market_discovery OK (N markets)
✓ strategy OK
✓ portfolio OK
✓ strategy_stats_empty OK
✓ pnl_from_resolved_positions OK
✓ trader paper mode OK

✓ All tests passed!
```

**Each test prints single-line summary upon success**

**No parallelization:** Tests run sequentially

## Test Design Philosophy

**Real integrations over mocks:** Tests call actual Gamma API, use real SQLite

**Pragmatic assertion:** String formatting in assertion messages for debugging
```python
assert stats["win_rate"] == 1.0, f"Expected 1.0 win_rate, got {stats['win_rate']}"
```

**Temp files for isolation:** Each test gets fresh temporary database path

**Single-file test suite:** All tests in one file for simplicity; no test discovery framework

---

*Testing analysis: 2026-03-25*
