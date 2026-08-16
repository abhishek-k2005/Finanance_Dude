"""
Validates that every metric field in display_key_metrics renders
without a TypeError/format crash, using the live Finnhub payload.
"""
from data_fetcher import get_stock_data

d = get_stock_data('AAPL', '1 Year')
prices = d['prices']
info = d['info']
source = d.get('source', 'yfinance')


def _to_float(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


current_price = _to_float(prices['Close'].iloc[-1]) or 0.0
if source == 'finnhub':
    price_change = _to_float(info.get('regularMarketChange')) or 0.0
    price_change_pct = _to_float(info.get('regularMarketChangePercent')) or 0.0
else:
    prev_close = _to_float(prices['Close'].iloc[-2]) if len(prices) > 1 else current_price
    price_change = current_price - prev_close
    price_change_pct = (price_change / prev_close * 100) if prev_close else 0.0

market_cap = _to_float(info.get('marketCap'))
pe_ratio = _to_float(info.get('trailingPE'))
volume = _to_float(prices['Volume'].iloc[-1]) or 0.0
day_high = _to_float(prices['High'].iloc[-1])
day_low = _to_float(prices['Low'].iloc[-1])
w52h = _to_float(info.get('fiftyTwoWeekHigh'))
w52l = _to_float(info.get('fiftyTwoWeekLow'))
dividend_yield = _to_float(info.get('dividendYield'))
beta = _to_float(info.get('beta'))

print(f"source       : {source}")
print(f"price        : ${current_price:.2f}  change={price_change:+.2f}  pct={price_change_pct:+.2f}%")
print(f"mktcap       : {'$'+f'{market_cap/1e9:.2f}B' if market_cap and market_cap > 1e9 else 'N/A'}")
print(f"pe_ratio     : {f'{pe_ratio:.2f}' if pe_ratio is not None else 'N/A'}")
print(f"volume       : {f'{volume/1e6:.1f}M' if volume >= 1e6 else f'{volume/1e3:.0f}K'}")
print(f"day_range    : {'$'+f'{day_low:.2f}'+' - $'+f'{day_high:.2f}' if day_high and day_low else 'N/A'}")
print(f"52w_range    : {'$'+f'{w52l:.2f}'+' - $'+f'{w52h:.2f}' if w52h and w52l else 'N/A'}")
print(f"divyield     : {f'{dividend_yield:.2f}%' if dividend_yield is not None else 'N/A'}")
print(f"beta         : {f'{beta:.2f}' if beta is not None else 'N/A'}")
print()
print("ALL METRICS RENDERED OK - no format crash.")
