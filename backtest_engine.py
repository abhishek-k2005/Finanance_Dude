import json
import math
import numpy as np
import pandas as pd
import yfinance as yf
from datetime import datetime

TRANSACTION_COST = 0.001
SLIPPAGE = 0.0005
RISK_FREE_RATE = 0.0
ANNUALIZATION_DAYS = 252


def _to_datetime(value):
    if isinstance(value, str):
        return pd.Timestamp(value)
    return pd.Timestamp(value)


def fetch_price_history(symbol: str, start_date: str = None, end_date: str = None):
    """Fetch price history from yfinance for a symbol range."""
    stock = yf.Ticker(symbol)

    if start_date and end_date:
        data = stock.history(start=start_date, end=end_date)
    elif start_date:
        data = stock.history(start=start_date)
    elif end_date:
        data = stock.history(end=end_date)
    else:
        data = stock.history(period="1y")

    if data is None or data.empty:
        raise ValueError(f"No price history found for {symbol}")

    data = data[['Close']].copy()
    data = data.dropna()
    data.columns = ['Close']
    return data


def compute_metrics(equity_curve: pd.Series, benchmark_curve: pd.Series = None, returns: pd.Series = None) -> dict:
    """Return a stable metric package for a cumulative equity series."""
    if len(equity_curve) < 2:
        return {
            'sharpe_ratio': 0.0,
            'sortino_ratio': 0.0,
            'max_drawdown': 0.0,
            'daily_return_mean': 0.0,
            'daily_return_std': 0.0,
            'annualized_return': 0.0,
        }

    start = equity_curve.iloc[0]
    end = equity_curve.iloc[-1]
    total_return = (end / start) - 1

    daily_returns = equity_curve.pct_change().dropna()
    if returns is not None:
        daily_returns = returns.dropna()

    daily_return_mean = float(daily_returns.mean()) if len(daily_returns) else 0.0
    daily_return_std = float(daily_returns.std()) if len(daily_returns) else 0.0

    if daily_return_std == 0:
        sharpe = 0.0
    else:
        sharpe = (daily_return_mean - RISK_FREE_RATE) / daily_return_std * math.sqrt(ANNUALIZATION_DAYS)

    downside = daily_returns[daily_returns < 0]
    sortino_denom = downside.std() if len(downside) else 0.0
    if sortino_denom == 0:
        sortino = 0.0
    else:
        sortino = (daily_return_mean - RISK_FREE_RATE) / sortino_denom * math.sqrt(ANNUALIZATION_DAYS)

    rolling_peak = equity_curve.cummax()
    drawdown = (equity_curve - rolling_peak) / rolling_peak
    max_drawdown = float(drawdown.min()) if len(drawdown) else 0.0

    annualized_return = (end / start) ** (ANNUALIZATION_DAYS / len(equity_curve)) - 1 if len(equity_curve) else 0.0

    return {
        'sharpe_ratio': float(sharpe),
        'sortino_ratio': float(sortino),
        'max_drawdown': float(max_drawdown),
        'daily_return_mean': float(daily_return_mean),
        'daily_return_std': float(daily_return_std),
        'annualized_return': float(annualized_return),
        'total_return': float(total_return),
    }


def bootstrap_sharpe_ci(daily_returns: pd.Series, samples: int = 1000) -> dict:
    """Non-parametric bootstrap confidence interval for Sharpe ratio."""
    returns = daily_returns.dropna().to_numpy()
    if len(returns) < 2:
        return {'lower': 0.0, 'upper': 0.0, 'point': 0.0}

    rng = np.random.default_rng(42)
    sharpe_values = []

    for _ in range(samples):
        sample = rng.choice(returns, size=len(returns), replace=True)
        if sample.std() == 0:
            sharpe = 0.0
        else:
            sharpe = (sample.mean() - RISK_FREE_RATE) / sample.std() * math.sqrt(ANNUALIZATION_DAYS)
        sharpe_values.append(float(sharpe))

    sharpe_values = np.array(sharpe_values)
    lower, upper = np.percentile(sharpe_values, [2.5, 97.5])
    point = (returns.mean() - RISK_FREE_RATE) / returns.std() * math.sqrt(ANNUALIZATION_DAYS) if returns.std() else 0.0

    return {
        'lower': float(lower),
        'upper': float(upper),
        'point': float(point),
        'samples': samples,
    }


def compute_benchmark(data: pd.DataFrame) -> pd.Series:
    """Buy and hold benchmark equity curve on the same symbol/data."""
    close = data['Close'].astype(float)
    benchmark = (close / close.iloc[0]).astype(float)
    return benchmark


def _apply_costs_and_slippage(close_price: float, direction: str):
    """Return execution price adjusted by costs and slippage."""
    if direction == 'buy':
        return close_price * (1 + SLIPPAGE + TRANSACTION_COST)
    return close_price * (1 - SLIPPAGE - TRANSACTION_COST)


def run_ma_crossover_backtest(symbol: str, fast_window: int = 10, slow_window: int = 30, start_date: str = None, end_date: str = None, ai_signal: dict = None):
    """Run a MA crossover strategy backtest with walk-forward validation and benchmark comparison."""
    if fast_window <= 1:
        raise ValueError('fast_window must be >= 2')
    if slow_window <= fast_window:
        raise ValueError('slow_window must be greater than fast_window')

    data = fetch_price_history(symbol, start_date=start_date, end_date=end_date)
    data = data[['Close']].copy()

    if data.empty:
        raise ValueError(f'No data available for {symbol}')

    close = data['Close'].astype(float)
    data['fast_ma'] = close.rolling(fast_window).mean()
    data['slow_ma'] = close.rolling(slow_window).mean()

    # Crossover signal: fast MA > slow MA changes from negative to positive -> bullish. Reverse -> bearish.
    signal = pd.Series(0, index=data.index, dtype=int)
    prev_fast = data['fast_ma'].shift(1)
    prev_slow = data['slow_ma'].shift(1)

    bullish_cross = (data['fast_ma'] > data['slow_ma']) & (prev_fast <= prev_slow)
    bearish_cross = (data['fast_ma'] < data['slow_ma']) & (prev_fast >= prev_slow)

    signal.loc[bullish_cross] = 1
    signal.loc[bearish_cross] = -1

    signal = signal.fillna(0)

    position = 0
    equity = 1.0
    equity_curve = [1.0]
    strategy = []
    daily_returns = []

    for i in range(1, len(data)):
        prev_close = float(close.iloc[i - 1])
        curr_close = float(close.iloc[i])
        daily_return = (curr_close / prev_close) - 1.0
        current_signal = int(signal.iloc[i])

        # Strategy always rebalances at bar close using the current signal with slippage and cost
        if current_signal == 1 and position == 0:
            # Buy on next bar close; take transaction cost and slippage on the execution fill
            fill_price = _apply_costs_and_slippage(curr_close, 'buy')
            execution_return = (fill_price / prev_close) - 1.0
            daily_return = daily_return + execution_return * 0.01
            position = 1
        elif current_signal == -1 and position == 1:
            fill_price = _apply_costs_and_slippage(curr_close, 'sell')
            execution_return = (fill_price / prev_close) - 1.0
            daily_return = daily_return + execution_return * 0.01
            position = 0

        if position == 1:
            daily_strategy_return = daily_return
        else:
            daily_strategy_return = 0.0

        equity *= (1.0 + daily_strategy_return)
        equity_curve.append(equity)
        strategy.append(daily_strategy_return)
        daily_returns.append(daily_strategy_return)

    equity_curve = pd.Series(equity_curve, index=data.index)
    daily_ret_series = pd.Series(strategy, index=data.index[1:])

    benchmark_curve = compute_benchmark(data)
    # normalize benchmark to unit equity as well
    benchmark_equity = pd.Series(1.0, index=data.index)
    benchmark_equity = benchmark_equity * benchmark_curve.iloc[0]
    benchmark_equity = benchmark_curve / benchmark_curve.iloc[0]

    strategy_equity = pd.Series(equity_curve, index=data.index)
    # Calculate metrics against the strategy series
    metrics = compute_metrics(strategy_equity, benchmark_curve, daily_ret_series)
    benchmark_metrics = compute_metrics(pd.Series(benchmark_equity, index=data.index), None, data['Close'].pct_change().dropna())

    ci = bootstrap_sharpe_ci(daily_ret_series, samples=1000)

    walk_forward = walk_forward_validate(data, fast_window, slow_window)

    ai_adjusted_profit_curve = None
    ai_adjusted_metrics = None
    ai_signal_summary = None
    if ai_signal:
        ai_signal_summary = {
            'management_tone_confidence': ai_signal.get('management_tone_confidence', 0.5),
            'guidance_sentiment': ai_signal.get('guidance_sentiment', 'neutral'),
            'hedging_language_density': ai_signal.get('hedging_language_density', 0.0),
            'semantic_drift': ai_signal.get('semantic_drift', 0.0),
        }
        ai_adjustment = 0.0
        tone = float(ai_signal.get('management_tone_confidence', 0.5))
        sentiment = str(ai_signal.get('guidance_sentiment', 'neutral')).lower()
        hedge = float(ai_signal.get('hedging_language_density', 0.0))

        if sentiment == 'positive':
            ai_adjustment += 0.05 * tone
        elif sentiment == 'negative':
            ai_adjustment -= 0.05 * tone

        ai_adjustment -= min(hedge / 10.0, 0.05)
        ai_adjustment += (tone - 0.5) * 0.03

        ai_scale = 1.0 + max(-0.25, min(0.25, ai_adjustment))
        ai_adjusted_returns = daily_ret_series * ai_scale
        ai_equity = 1.0
        ai_curve = [1.0]
        for value in ai_adjusted_returns:
            ai_equity *= (1.0 + value)
            ai_curve.append(ai_equity)

        ai_adjusted_profit_curve = pd.Series(ai_curve, index=data.index)
        ai_adjusted_metrics = compute_metrics(ai_adjusted_profit_curve, None, ai_adjusted_returns)

    return {
        'symbol': symbol.upper(),
        'fast_window': fast_window,
        'slow_window': slow_window,
        'start_date': start_date or data.index[0].strftime('%Y-%m-%d'),
        'end_date': end_date or data.index[-1].strftime('%Y-%m-%d'),
        'metrics': {
            'sharpe_ratio': metrics['sharpe_ratio'],
            'sortino_ratio': metrics['sortino_ratio'],
            'max_drawdown': metrics['max_drawdown'],
            'annualized_return': metrics['annualized_return'],
            'total_return': metrics['total_return'],
        },
        'benchmark_metrics': {
            'sharpe_ratio': benchmark_metrics['sharpe_ratio'],
            'sortino_ratio': benchmark_metrics['sortino_ratio'],
            'max_drawdown': benchmark_metrics['max_drawdown'],
            'annualized_return': benchmark_metrics['annualized_return'],
            'total_return': benchmark_metrics['total_return'],
        },
        'sharpe_ci_95': {
            'lower': ci['lower'],
            'upper': ci['upper'],
        },
        'equity_curve': [{'date': date.isoformat() if hasattr(date, 'isoformat') else str(date), 'value': float(value)} for date, value in strategy_equity.items()],
        'benchmark_equity_curve': [{'date': date.isoformat() if hasattr(date, 'isoformat') else str(date), 'value': float(value)} for date, value in pd.Series(benchmark_equity, index=data.index).items()],
        'walk_forward_validation': walk_forward,
        'ablation': {
            'technical_only': {
                'sharpe_ratio': metrics['sharpe_ratio'],
                'sortino_ratio': metrics['sortino_ratio'],
                'max_drawdown': metrics['max_drawdown'],
            },
            'technical_plus_ai': {
                'sharpe_ratio': ai_adjusted_metrics['sharpe_ratio'] if ai_adjusted_metrics else metrics['sharpe_ratio'],
                'sortino_ratio': ai_adjusted_metrics['sortino_ratio'] if ai_adjusted_metrics else metrics['sortino_ratio'],
                'max_drawdown': ai_adjusted_metrics['max_drawdown'] if ai_adjusted_metrics else metrics['max_drawdown'],
                'ai_signal': ai_signal_summary,
            } if ai_signal else None,
        },
    }


def walk_forward_validate(data: pd.DataFrame, fast_window: int, slow_window: int):
    """Create an expanding-window validation split and summarize each fold."""
    prices = data[['Close']].copy()
    if len(prices) < slow_window + 30:
        return {
            'folds': [],
            'status': 'insufficient_data_for_walk_forward',
        }

    test_size = max(20, min(60, len(prices) // 5))
    initial_train = max(slow_window, len(prices) // 3)

    folds = []
    fold_start = initial_train
    while fold_start + test_size < len(prices):
        train_rows = prices.iloc[:fold_start]
        test_rows = prices.iloc[fold_start:fold_start + test_size]

        fold_equity = run_walk_fold(train_rows, test_rows, fast_window, slow_window)
        fold_metrics = compute_metrics(fold_equity)
        folds.append({
            'train_end_index': int(fold_start),
            'test_start': test_rows.index[0].strftime('%Y-%m-%d'),
            'test_end': test_rows.index[-1].strftime('%Y-%m-%d'),
            'sharpe_ratio': fold_metrics['sharpe_ratio'],
            'sortino_ratio': fold_metrics['sortino_ratio'],
            'max_drawdown': fold_metrics['max_drawdown'],
        })
        fold_start += test_size

    return {
        'folds': folds,
        'fold_count': len(folds),
        'status': 'ok' if folds else 'insufficient_data',
    }


def run_walk_fold(train_rows: pd.DataFrame, test_rows: pd.DataFrame, fast_window: int, slow_window: int):
    """Run a single expanding-window MA crossover over a test subset."""
    combined = pd.concat([train_rows, test_rows])
    close = combined['Close'].astype(float)
    fast_ma = close.rolling(fast_window).mean()
    slow_ma = close.rolling(slow_window).mean()

    positions = pd.Series(0, index=combined.index, dtype=int)
    prev_fast = fast_ma.shift(1)
    prev_slow = slow_ma.shift(1)
    bullish = (fast_ma > slow_ma) & (prev_fast <= prev_slow)
    bearish = (fast_ma < slow_ma) & (prev_fast >= prev_slow)
    positions.loc[bullish] = 1
    positions.loc[bearish] = -1

    position = 0
    equity = 1.0
    equity_curve = [1.0]
    for i in range(1, len(combined)):
        daily_ret = (close.iloc[i] / close.iloc[i - 1]) - 1.0
        if positions.iloc[i] == 1 and position == 0:
            position = 1
        elif positions.iloc[i] == -1 and position == 1:
            position = 0

        strategy_ret = daily_ret if position == 1 else 0.0
        equity *= (1.0 + strategy_ret)
        equity_curve.append(equity)

    return pd.Series(equity_curve, index=combined.index)
