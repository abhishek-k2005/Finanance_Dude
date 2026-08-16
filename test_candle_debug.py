"""Diagnose candle endpoint response and cache state."""
import os, time, requests

api_key = os.getenv("FINNHUB_API_KEY", "")
print(f"API key present: {bool(api_key)} (len={len(api_key)})")

now = int(time.time())
from_ts = now - 365 * 86400
print(f"from_ts={from_ts}  to_ts={now}  delta_days={(now-from_ts)//86400}")

base = "https://finnhub.io/api/v1"
params = {
    "symbol": "AAPL",
    "resolution": "D",
    "from": from_ts,
    "to": now,
    "token": api_key,
}
print(f"\nGET /stock/candle with params: { {k:v for k,v in params.items() if k != 'token'} }")

resp = requests.get(f"{base}/stock/candle", params=params, timeout=15)
print(f"HTTP status: {resp.status_code}")
data = resp.json()
print(f"Response keys: {list(data.keys())}")
print(f"status (s)  : {data.get('s')}")
t_list = data.get("t", [])
c_list = data.get("c", [])
print(f"timestamps  : {len(t_list)} entries")
print(f"close prices: {len(c_list)} entries")
if t_list:
    import pandas as pd
    first = pd.to_datetime(t_list[0], unit='s', utc=True)
    last  = pd.to_datetime(t_list[-1], unit='s', utc=True)
    print(f"date range  : {first} → {last}")
    print(f"first 3     : {c_list[:3]}")
    print(f"last  3     : {c_list[-3:]}")
else:
    print("Full response:", data)

# Also test yfinance directly
print("\n--- yfinance direct test ---")
import yfinance as yf
stock = yf.Ticker("AAPL")
hist = stock.history(period="1y")
print(f"yfinance rows: {len(hist)}")
if not hist.empty:
    print(f"date range: {hist.index[0]} → {hist.index[-1]}")
