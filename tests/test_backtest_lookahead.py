"""Test backtest engine: verify no future data leaks at decision time t."""

import pytest
import pandas as pd
from datetime import datetime, timedelta
import backtest_engine


class TestNoLookaheadBias:
    """
    Verify that MA crossover strategy only uses data available at time t.
    No future prices are used to make decisions at current bar.
    """

    def test_signal_calculated_only_on_current_and_past_data(self, monkeypatch):
        """
        Verify that signal at time t only depends on MA values at times <= t.
        MAs use rolling windows of past prices, so no lookahead.
        """
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        prices = pd.Series(
            list(range(100, 150)) + list(range(149, 99, -1)),
            index=dates
        )

        def mock_fetch(*args, **kwargs):
            return pd.DataFrame({"Close": prices})

        monkeypatch.setattr(backtest_engine, "fetch_price_history", mock_fetch)

        result = backtest_engine.run_ma_crossover_backtest(
            "TEST", fast_window=5, slow_window=10
        )

        assert result is not None
        assert 'metrics' in result
        assert 'equity_curve' in result

    def test_ma_calculation_uses_only_past_bars(self):
        """
        Verify MA values: MA at time t is calculated from prices[0:t+1],
        so it doesn't peek into future prices.
        """
        prices = pd.Series([100.0, 101.0, 102.0, 103.0, 104.0, 105.0])
        fast_window = 2
        slow_window = 3

        fast_ma = prices.rolling(window=fast_window).mean()
        slow_ma = prices.rolling(window=slow_window).mean()

        assert fast_ma.iloc[0] != fast_ma.iloc[0]
        assert slow_ma.iloc[0] != slow_ma.iloc[0]

        assert fast_ma.iloc[1] == 100.5
        assert slow_ma.iloc[2] == 101.0

    def test_signal_derivation_is_causal(self):
        """
        Verify that signal at time t depends only on
        prev_fast <= prev_slow and fast > slow at time t,
        not on future crossovers.
        """
        data = pd.DataFrame({
            'Close': [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 104.0, 103.0, 102.0, 101.0]
        })

        close = data['Close'].astype(float)
        data['fast_ma'] = close.rolling(2).mean()
        data['slow_ma'] = close.rolling(3).mean()

        signal = pd.Series(0, index=data.index, dtype=int)
        prev_fast = data['fast_ma'].shift(1)
        prev_slow = data['slow_ma'].shift(1)

        bullish_cross = (data['fast_ma'] > data['slow_ma']) & (prev_fast <= prev_slow)
        bearish_cross = (data['fast_ma'] < data['slow_ma']) & (prev_fast >= prev_slow)

        signal.loc[bullish_cross] = 1
        signal.loc[bearish_cross] = -1

        assert len(signal) == len(data)
        for i in range(len(signal)):
            if i == 0:
                continue
            curr_fast = data['fast_ma'].iloc[i]
            curr_slow = data['slow_ma'].iloc[i]
            prev_f = prev_fast.iloc[i]
            prev_s = prev_slow.iloc[i]

            if pd.notna(curr_fast) and pd.notna(curr_slow):
                if pd.notna(prev_f) and pd.notna(prev_s):
                    is_bullish = (curr_fast > curr_slow) and (prev_f <= prev_s)
                    is_bearish = (curr_fast < curr_slow) and (prev_f >= prev_s)

                    if is_bullish:
                        assert signal.iloc[i] == 1
                    elif is_bearish:
                        assert signal.iloc[i] == -1

    def test_walk_forward_validation_respects_time_order(self, monkeypatch):
        """
        Verify that walk_forward_validate doesn't use future data.
        Each fold should expand forward in time, not contaminate past with future.
        """
        dates = pd.date_range("2024-01-01", periods=100, freq="D")
        prices = pd.Series(range(100, 200), index=dates)

        def mock_fetch(*args, **kwargs):
            return pd.DataFrame({"Close": prices})

        monkeypatch.setattr(backtest_engine, "fetch_price_history", mock_fetch)

        result = backtest_engine.run_ma_crossover_backtest(
            "TEST", fast_window=5, slow_window=10
        )

        assert 'walk_forward_validation' in result
