"""Test that get_stock_data returns a proper time series, not a 1-row snapshot."""
from data_fetcher import get_stock_data
import time

# Test actual fetch
for period in ["1 Year", "2 Years"]:
    print(f"--- get_stock_data('AAPL', {period!r}) ---")
    start = time.time()
    d = get_stock_data("AAPL", period)
    elapsed = time.time() - start
    prices = d["prices"]
    print(f"  source       : {d['source']}")
    print(f"  rows         : {len(prices)}  (expected ~252 for 1y, ~504 for 2y)")
    print(f"  columns      : {list(prices.columns)}")
    print(f"  date range   : {prices.index[0]} → {prices.index[-1]}")
    print(f"  elapsed      : {elapsed:.1f}s")
    print(f"  PASS         : {len(prices) > 10}")
    print()
