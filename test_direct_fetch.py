"""Test bypassing cache — directly call _fetch_finnhub_payload."""
import sys
# Force reimport from disk
import importlib
import data_fetcher
importlib.reload(data_fetcher)

from data_fetcher import _fetch_finnhub_payload, CACHE_STORE

# Clear the in-process cache
CACHE_STORE.clear()
print(f"Cache cleared. Keys: {list(CACHE_STORE.keys())}")

import time

for period in ["1 Year"]:
    print(f"\n--- _fetch_finnhub_payload('AAPL', {period!r}) ---")
    start = time.time()
    d = _fetch_finnhub_payload("AAPL", period)
    elapsed = time.time() - start
    if d is None:
        print("  returned None!")
    else:
        prices = d["prices"]
        print(f"  source     : {d['source']}")
        print(f"  rows       : {len(prices)}")
        print(f"  columns    : {list(prices.columns)}")
        if len(prices) > 1:
            print(f"  date range : {prices.index[0]} → {prices.index[-1]}")
        print(f"  elapsed    : {elapsed:.1f}s")
        print(f"  PASS       : {len(prices) > 10}")
