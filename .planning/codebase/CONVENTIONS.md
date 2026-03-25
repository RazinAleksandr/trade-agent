# Coding Conventions

**Analysis Date:** 2026-03-25

## Naming Patterns

**Files:**
- All lowercase with underscores: `market_discovery.py`, `data_store.py`, `logger_setup.py`
- Purpose-driven names: module file names match their primary class/function (e.g., `strategy.py` contains `kelly_criterion()` and `TradeSignal`)
- Test files follow pattern: `test_*.py` in `tests/` directory

**Functions:**
- Snake case: `fetch_active_markets()`, `batch_analyze()`, `kelly_criterion()`
- Private functions prefixed with underscore: `_parse_market()`, `_passes_filters()`, `_evaluate_signal()`, `_extract_json_from_response()`
- Descriptive verb-noun pattern: `record_trade()`, `upsert_position()`, `check_risk_limits()`

**Variables:**
- Snake case throughout: `cycle_start`, `remaining_capital`, `estimated_prob`, `kelly_adjusted`
- Boolean flags: `paper_mode`, `is_paper`, `shutdown_requested`
- Constants in UPPERCASE: `PRIVATE_KEY`, `OPENAI_API_KEY`, `MAX_POSITION_SIZE_USDC` (in `config.py`)
- Loop variables: `m` for market, `t` for trade, `pos` for position, `c` for closed position (single letter for short-lived iterations)

**Types:**
- Dataclasses for data models: `@dataclass` used in `TradeSignal`, `Market`, `MarketAnalysis`, `OrderResult`
- Type hints on function parameters and returns: `def kelly_criterion(prob: float, odds_price: float, fraction: float = config.KELLY_FRACTION) -> float`
- Optional types: `Optional[ClobClient]`, `MarketAnalysis | None` (Python 3.12+ union syntax)
- Return type alternatives: `list[Market]`, `dict[str, float]`

## Code Style

**Formatting:**
- No explicit formatter (Black/ruff) configured — follows PEP 8 manually
- Indentation: 4 spaces
- Line length: practical limit ~100 characters (observed in code)
- Imports grouped: stdlib → third-party → local (with blank lines between groups)
- Trailing commas in multi-line structures

**Linting:**
- No linter config found (no `.pylintrc`, `.flake8`, etc.)
- Code assumes PEP 8 style is maintained by convention
- Type hints used throughout but not enforced by mypy or similar

**Import order observed:**
1. Standard library: `import json`, `import os`, `import sqlite3`
2. Third-party: `from openai import OpenAI`, `from py_clob_client.client import ClobClient`
3. Local modules: `import config`, `from strategy import TradeSignal`

**Example imports from `main.py`:**
```python
import time
import signal
import sys
from datetime import datetime, timezone

import config
from logger_setup import get_logger, log_decision
from data_store import DataStore
from market_discovery import fetch_active_markets, fetch_market_by_id
```

## Error Handling

**Pattern:** Broad try-except with logging, return safe defaults

Common pattern in API/external calls:
```python
try:
    resp = requests.get(...)
    resp.raise_for_status()
    return parsed_result
except Exception as e:
    log.error(f"Description: {e}")
    return []  # or None or empty dict
```

**Examples:**
- `fetch_active_markets()` in `market_discovery.py`: returns empty list on error
- `analyze_market()` in `market_analyzer.py`: returns None on JSON decode or OpenAI error
- `batch_analyze()`: catches individual failures but continues processing
- `_init_live_client()` in `trader.py`: catches and logs, falls back to paper mode

**No exception re-raising:** Errors are logged but not propagated — caller gets safe default instead

**JSON parsing resilience:** `_extract_json_from_response()` in `market_analyzer.py` tries multiple approaches:
1. Direct parse
2. Markdown code blocks
3. Regex JSON extraction
Raises `json.JSONDecodeError` only after all attempts fail

## Logging

**Framework:** Python's standard `logging` module

**Initialization:** `get_logger(name)` in `logger_setup.py` returns configured logger
```python
log = get_logger("main")
log = get_logger("strategy")
log = get_logger("market_discovery")
```

**Patterns:**
- Info level: progress and cycle info — `log.info(f"Step 1: Discovering markets...")`
- Warning level: non-blocking issues — `log.warning(f"Could not fetch market {signal.market_id}")`
- Error level: failures with fallback — `log.error(f"Market discovery failed: {e}")`

**Dual outputs:**
- Console: human-readable with timestamp, level, module name
- File (`trading.log`): JSON format for machine parsing

**Decision logging:** `log_decision(logger, decision_type, data)` for important decisions
```python
log_decision(log, "trade_signal", {
    "market_id": signal.market_id,
    "side": signal.side,
    "price": signal.price,
    "edge": signal.edge,
})
```

**No debug logging:** All active logs are INFO/WARNING/ERROR level

## Comments

**When to comment:**
- Non-obvious algorithm explanation: Kelly criterion math in `strategy.py`
- Data format details: "Handle stringified JSON from Gamma API" in `market_discovery.py`
- Workarounds and tricky logic: "minimum $1 trade" threshold

**JSDoc/docstring style:**
- Docstrings on functions/classes: triple-quoted, brief description first
- Example from `strategy.py`:
```python
def kelly_criterion(prob: float, odds_price: float, fraction: float = config.KELLY_FRACTION) -> float:
    """
    Fractional Kelly criterion for binary outcome.
    prob: estimated true probability of winning
    odds_price: price we pay per share (payout is 1.0 on win)
    fraction: Kelly fraction (0.25 = quarter Kelly for safety)

    Returns fraction of bankroll to bet.
    """
```

**Inline comments:** Minimal; reserved for logic that isn't self-documenting

**No docstrings on simple getters/setters** — only on complex functions

## Function Design

**Size:** Most functions 10-50 lines; longer functions (50-100 lines) are orchestration loops

**Parameters:**
- Positional for required params: `def kelly_criterion(prob: float, odds_price: float, ...)`
- Keyword-only config defaults: functions use `config.KELLY_FRACTION`, `config.MAX_POSITION_SIZE_USDC`
- Dataclass parameters preferred over many positional args

**Return values:**
- Single return type per function
- Dataclasses for multi-field returns: `TradeSignal`, `OrderResult`, `MarketAnalysis`
- None for side-effect-only functions: `update_position_prices()`, `record_trade()`
- Safe defaults on error: `[]`, `None`, `{}`, `False`

**No mutable default arguments:** Uses `field(default_factory=list)` in dataclasses

## Module Design

**Exports:** All public functions/classes at module level; no `__all__` definition observed

**Module structure (flat):**
- No subpackages; all `.py` files in project root per design
- Each module focused: `market_discovery.py` for Gamma API, `trader.py` for execution, `data_store.py` for persistence

**Barrel files:** Not used in this codebase

**Initialization:** `config.py` loads environment at import time
```python
from dotenv import load_dotenv
load_dotenv()
# All constants initialized here
```

Modules import `config` for parameters, not passed as arguments:
```python
# In market_discovery.py
def fetch_active_markets(
    limit: int = config.MAX_MARKETS_PER_CYCLE,
    min_volume: float = config.MIN_VOLUME_24H,
    ...
```

## Architecture Patterns

**Dataclasses over dicts:** Strongly preferred
- `Market`, `TradeSignal`, `MarketAnalysis`, `OrderResult` are dataclasses
- Cleaner than `{"market_id": "...", "price": 0.5}`

**Dependency injection:** Services accept store/config objects
```python
class Trader:
    def __init__(self, store: DataStore):
        self.store = store
        self.paper_mode = config.PAPER_TRADING
```

**Optional client initialization:** `Trader` lazy-initializes live client, falls back to paper mode

**Separation of concerns:**
- `market_discovery.py`: API calls only
- `market_analyzer.py`: LLM analysis only
- `strategy.py`: signal generation (pure logic)
- `trader.py`: execution
- `portfolio.py`: position tracking and risk

---

*Convention analysis: 2026-03-25*
