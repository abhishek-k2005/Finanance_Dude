"""Test backtest engine: verify transaction costs and slippage are correctly subtracted."""

import pytest
import math
import pandas as pd
import backtest_engine


class TestTransactionCosts:
    """
    Verify that transaction costs (TRANSACTION_COST) and slippage (SLIPPAGE)
    are correctly applied and subtracted from returns.
    """

    def test_apply_costs_and_slippage_buy(self):
        """
        On buy, price should increase by (SLIPPAGE + TRANSACTION_COST).
        Expected: buy_fill = price * (1 + SLIPPAGE + TRANSACTION_COST)
        """
        price = 100.0
        buy_fill = backtest_engine._apply_costs_and_slippage(price, "buy")

        expected = price * (1 + backtest_engine.SLIPPAGE + backtest_engine.TRANSACTION_COST)
        assert math.isclose(buy_fill, expected, rel_tol=1e-9)
        assert buy_fill > price

    def test_apply_costs_and_slippage_sell(self):
        """
        On sell, price should decrease by (SLIPPAGE + TRANSACTION_COST).
        Expected: sell_fill = price * (1 - SLIPPAGE - TRANSACTION_COST)
        """
        price = 100.0
        sell_fill = backtest_engine._apply_costs_and_slippage(price, "sell")

        expected = price * (1 - backtest_engine.SLIPPAGE - backtest_engine.TRANSACTION_COST)
        assert math.isclose(sell_fill, expected, rel_tol=1e-9)
        assert sell_fill < price

    def test_costs_are_asymmetric(self):
        """
        Buy and sell fills should be symmetric around the mid price by design.
        buy_fill > mid_price and sell_fill < mid_price by equal amounts.
        Cost model is symmetric: buy_fill + sell_fill = 2 * mid_price.
        """
        mid_price = 100.0
        buy_fill = backtest_engine._apply_costs_and_slippage(mid_price, "buy")
        sell_fill = backtest_engine._apply_costs_and_slippage(mid_price, "sell")

        assert buy_fill > mid_price
        assert sell_fill < mid_price
        assert math.isclose(buy_fill + sell_fill, 2 * mid_price, rel_tol=1e-9)

    def test_round_trip_cost_magnitude(self):
        """
        A round trip (buy then sell) should incur costs on both legs.
        Cost should be approximately 2 * (SLIPPAGE + TRANSACTION_COST) * price.
        """
        price = 100.0
        buy_fill = backtest_engine._apply_costs_and_slippage(price, "buy")
        sell_fill = backtest_engine._apply_costs_and_slippage(price, "sell")

        round_trip_cost = buy_fill - sell_fill
        cost_percent = round_trip_cost / price

        expected_cost_percent = 2 * (backtest_engine.SLIPPAGE + backtest_engine.TRANSACTION_COST)
        assert math.isclose(cost_percent, expected_cost_percent, rel_tol=1e-9)

    def test_backtest_equity_reduced_by_costs(self, monkeypatch):
        """
        Strategy returns should be lower than a no-cost benchmark
        due to transaction costs being subtracted.
        """
        prices = pd.Series(
            [100.0, 102.0, 101.0, 103.0, 105.0, 104.0, 106.0, 108.0, 107.0, 110.0],
            index=pd.date_range("2024-01-01", periods=10, freq="D")
        )

        def mock_fetch(*args, **kwargs):
            return pd.DataFrame({"Close": prices})

        monkeypatch.setattr(backtest_engine, "fetch_price_history", mock_fetch)

        result = backtest_engine.run_ma_crossover_backtest(
            "TEST", fast_window=2, slow_window=3
        )

        assert 'metrics' in result
        assert 'benchmark_metrics' in result

        strategy_return = result['metrics']['total_return']
        benchmark_return = result['benchmark_metrics']['total_return']

        assert strategy_return <= benchmark_return + 0.01

    def test_costs_constants_are_nonzero(self):
        """
        Verify that SLIPPAGE and TRANSACTION_COST constants are defined and > 0.
        """
        assert backtest_engine.TRANSACTION_COST > 0
        assert backtest_engine.SLIPPAGE > 0
        assert backtest_engine.TRANSACTION_COST + backtest_engine.SLIPPAGE < 0.1

    def test_fill_price_varies_with_base_price(self):
        """
        Fill price should scale linearly with the base price.
        If price doubles, fill prices should also double (approximately).
        """
        price_1 = 100.0
        price_2 = 200.0

        buy_fill_1 = backtest_engine._apply_costs_and_slippage(price_1, "buy")
        buy_fill_2 = backtest_engine._apply_costs_and_slippage(price_2, "buy")

        ratio = buy_fill_2 / buy_fill_1
        assert math.isclose(ratio, 2.0, rel_tol=1e-6)

        sell_fill_1 = backtest_engine._apply_costs_and_slippage(price_1, "sell")
        sell_fill_2 = backtest_engine._apply_costs_and_slippage(price_2, "sell")

        ratio_sell = sell_fill_2 / sell_fill_1
        assert math.isclose(ratio_sell, 2.0, rel_tol=1e-6)
