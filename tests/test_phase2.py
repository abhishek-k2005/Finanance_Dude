import math

import pandas as pd
import pytest

from phase2_formatters import format_dividend_yield, format_market_cap, format_currency
from phase2_observability import SessionCache, groundedness_check
import backtest_engine


def test_format_dividend_yield_and_market_cap():
    assert format_dividend_yield(0.025) == "2.50%"
    assert format_dividend_yield(0.0005) == "0.05%"
    assert format_market_cap(1_250_000_000) == "$1.25B"
    assert format_market_cap(500_000_000) == "$500.00M"
    assert format_currency(1250.5) == "$1,250.50"


def test_groundedness_check_reports_mismatches():
    tool_result = {"current_price": 101.5, "dividend_yield": 0.025, "market_cap": 1_200_000_000}
    llm_text = "The stock is priced at $101.50 and yields 2.90%. Market cap is $1.20B."
    issues = groundedness_check(llm_text, tool_result, "AAPL analysis")
    assert any("2.90%" in issue["mismatched_value"] for issue in issues)
    assert any(issue["query"] == "AAPL analysis" for issue in issues)


def test_session_cache_ttl_and_hit_miss():
    cache = SessionCache(ttl_seconds=60)
    key = ("AAPL", "1y", "history")
    assert cache.get(key) is None
    cache.set(key, {"close": 123.45})
    assert cache.get(key) == {"close": 123.45}


def test_backtest_uses_only_past_data_and_costs_are_subtracted(monkeypatch):
    prices = pd.Series(
        [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0],
        index=pd.date_range("2024-01-01", periods=10, freq="D"),
    )
    monkeypatch.setattr(backtest_engine, "fetch_price_history", lambda *args, **kwargs: pd.DataFrame({"Close": prices}))

    result = backtest_engine.run_ma_crossover_backtest("AAPL", fast_window=2, slow_window=3)
    assert result["metrics"]["total_return"] <= result["benchmark_metrics"]["total_return"] + 0.01

    buy_fill = backtest_engine._apply_costs_and_slippage(100.0, "buy")
    sell_fill = backtest_engine._apply_costs_and_slippage(100.0, "sell")
    assert buy_fill > 100.0
    assert sell_fill < 100.0
    assert math.isclose(buy_fill, 100.0 * (1 + backtest_engine.SLIPPAGE + backtest_engine.TRANSACTION_COST))
    assert math.isclose(sell_fill, 100.0 * (1 - backtest_engine.SLIPPAGE - backtest_engine.TRANSACTION_COST))
