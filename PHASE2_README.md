# Phase 2: Observability, Caching, and Tests

This document describes Phase 2 implementation without modifying Phase 0/1 logic.

## 1. Observability (`observability.py`)

### Structured JSON Logging
- All events logged as JSON for machine parsing
- Fields: `timestamp`, `event_type`, custom metadata

### Tracing Decorators

#### `@trace_llm_call`
Wraps LLM calls and logs:
- Input size (bytes)
- Output size (bytes)
- Latency (seconds)
- Estimated cost (USD, based on token count)

Usage:
```python
from observability import trace_llm_call

@trace_llm_call
def call_llm(prompt):
    return client.chat.completions.create(...)
```

#### `@trace_tool_call`
Wraps data-fetch and tool calls and logs:
- Input/output sizes
- Latency
- Cost estimate
- Error status if failed

Usage:
```python
from observability import trace_tool_call

@trace_tool_call
def get_stock_data(symbol):
    return fetch_from_api(symbol)
```

### Groundedness Checking

**Function:** `check_groundedness(llm_response, grounding_data, query)`

Extracts numbers from LLM response and verifies they exist in the grounding data.
- **Format support:** $4561.70B, 16.4M, +0.16, +0.05%, plain decimals
- **Behavior:** Log-only (non-blocking)
- **Return:** Dict with `passed` flag and list of `mismatches`

Example:
```python
from observability import check_groundedness

result = check_groundedness(
    "AAPL is priced at $150.25 with a 2.5% dividend yield.",
    {"current_price": 150.25, "dividend_yield": 0.025},
    "AAPL analysis"
)
# result['passed'] == True
# result['mismatches'] == []
```

---

## 2. Caching (`cache_manager.py`)

### SessionCache Class

In-memory cache with TTL and per-(symbol, timeframe, query_type) keys.

```python
from cache_manager import SessionCache, cache_result, global_session_cache

cache = SessionCache(ttl_seconds=600)

# Manual cache operations
cache.get("AAPL", "1y", "stock_data")
cache.put("AAPL", "1y", "stock_data", {...})
cache.clear()

# Decorator usage
@cache_result(global_session_cache, "stock_data")
def get_stock_data(symbol: str, timeframe: str):
    return fetch_from_api(symbol, timeframe)
```

### Features
- **Key scheme:** `(symbol.upper(), timeframe, query_type)`
- **TTL default:** 600 seconds (10 min) — configurable
- **Logging:** Cache hits/misses/expirations logged as JSON events
- **Stats:** `cache.stats()` returns entry count, total size, keys

---

## 3. Formatters (`phase2_formatters.py`)

Display formatters for financial data, unit-tested for correctness.

### Functions

| Function | Input | Output | Example |
|----------|-------|--------|---------|
| `format_dividend_yield(value)` | float (0.025) | str | "2.50%" |
| `format_market_cap(value)` | float (1.25e9) | str | "$1.25B" |
| `format_currency(value)` | float (1250.5) | str | "$1,250.50" |
| `format_pe_ratio(value)` | float (25.5) | str | "25.50" |
| `format_percent_change(value)` | float (0.025) | str | "+2.50%" |

All formatters return "N/A" for None or invalid inputs.

---

## 4. Phase 2 Observability Wrapper (`phase2_observability.py`)

Convenience module bridging `observability.py` to test suite.

### SessionCache
Alias for `cache_manager.SessionCache` with dict-based key support.

```python
from phase2_observability import SessionCache

cache = SessionCache(ttl_seconds=60)
key = ("AAPL", "1y", "history")
cache.set(key, {...})
value = cache.get(key)
```

### groundedness_check Function
Wrapper around `observability.check_groundedness()`.
Returns list of mismatch dicts for easy test assertion.

```python
from phase2_observability import groundedness_check

issues = groundedness_check(
    "AAPL yields 2.90%.",
    {"dividend_yield": 0.025},
    "AAPL analysis"
)
# issues is a list; empty if groundedness passes
```

---

## 5. Tests

### `tests/test_formatters.py`
Unit tests for formatter functions.
- Dividend yield: 0.025 → "2.50%"
- Market cap: 1.25B → "$1.25B"
- Currency: 1250.5 → "$1,250.50"
- Handles N/A and invalid inputs

Run:
```bash
pytest tests/test_formatters.py -v
```

### `tests/test_backtest_lookahead.py`
Verify backtest engine does NOT use future data.
- MA calculations use only past bars
- Signal derivation is causal (depends on t-1, t only)
- Walk-forward validation respects time order

Run:
```bash
pytest tests/test_backtest_lookahead.py -v
```

### `tests/test_transaction_costs.py`
Verify transaction costs and slippage are correctly subtracted.
- Buy fill: price * (1 + SLIPPAGE + TRANSACTION_COST)
- Sell fill: price * (1 - SLIPPAGE - TRANSACTION_COST)
- Round-trip cost is ~2x single-leg cost
- Strategy equity < benchmark equity (due to costs)

Run:
```bash
pytest tests/test_transaction_costs.py -v
```

---

## Integration with Phase 0/1

Phase 2 code **does not modify** Phase 0/1 logic:
- `finance.py`, `data_fetcher.py`, `backtest_engine.py` unchanged
- Decorators and formatters are applied at the call site or display layer, not in core logic
- Caching can wrap existing functions without breaking them

To integrate caching:
```python
from cache_manager import global_session_cache, cache_result

# In agent/finance.py or data_fetcher.py:
@cache_result(global_session_cache, "stock_data")
def get_stock_data(symbol: str, timeframe: str):
    return dashboard_get_stock_data(symbol, timeframe)
```

To integrate observability:
```python
from observability import trace_tool_call, trace_llm_call

# Wrap existing functions
trace_llm_call(llm_call_fn)
trace_tool_call(api_fetch_fn)
```

---

## Examples

### Observability in Action

```python
from observability import trace_tool_call, check_groundedness

@trace_tool_call
def fetch_stock(symbol):
    return api.get(symbol)  # logs cost, latency, size

result = fetch_stock("AAPL")  # JSON log emitted

check_groundedness(
    llm_response="AAPL trades at $150.25 with a 2.5% yield.",
    grounding_data=result,
    query="AAPL analysis"
)  # logs match/mismatch
```

### Caching in Action

```python
from cache_manager import SessionCache

cache = SessionCache(ttl_seconds=300)

def get_stock_data(symbol, timeframe):
    key = (symbol, timeframe, "history")
    cached = cache.get(key)
    if cached:
        return cached  # cache hit logged
    
    result = fetch_api(symbol, timeframe)
    cache.put(key, result)  # stored, logged
    return result
```

### Formatting in Action

```python
from phase2_formatters import format_market_cap, format_dividend_yield

info = {
    "marketCap": 2.5e12,
    "dividendYield": 0.032
}

print(f"Market Cap: {format_market_cap(info['marketCap'])}")  # "$2.50B"
print(f"Dividend: {format_dividend_yield(info['dividendYield'])}")  # "3.20%"
```

---

## Notes

- **Logging destination:** stderr by default (Python logging). Redirect with handlers if needed.
- **Cache TTL:** Default 10 min. Market data staleness is a tunable knob.
- **Groundedness:** Non-blocking. Mismatches logged for observability; do not halt response.
- **Test running:** All tests use pytest. Run entire suite with `pytest tests/`.
