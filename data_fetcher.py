import copy
import time

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from yfinance.exceptions import YFRateLimitError


REQUEST_SESSION = requests.Session()
REQUEST_SESSION.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
    'Accept': 'application/json,text/html,*/*',
})

CACHE_TTL_SECONDS = 300
CACHE_STORE = {}


def calculate_rsi(prices, window=14):
    """Calculate RSI indicator without any Streamlit dependency."""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_technical_indicators(df):
    """Calculate technical indicators on a price DataFrame."""
    df = df.copy()
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=50).mean()
    df['SMA_200'] = df['Close'].rolling(window=200).mean()

    df['RSI'] = calculate_rsi(df['Close'])

    df['Daily_Return'] = df['Close'].pct_change()

    df['Volatility'] = df['Daily_Return'].rolling(window=20).std() * np.sqrt(252)

    return df


def _cache_is_fresh(symbol, period):
    """Return a cached payload if it sits inside the five-minute TTL."""
    key = f"{symbol.upper()}::{period}".strip()
    entry = CACHE_STORE.get(key)
    if not entry:
        return None

    now = time.time()
    if now - entry.get('fetched_at', 0) <= CACHE_TTL_SECONDS:
        return copy.deepcopy(entry.get('payload'))

    # TTL expired: discard this cache entry.
    CACHE_STORE.pop(key, None)
    return None


def _get_stale_cache(symbol, period):
    """Return the last known cache payload when the live API reaches a rate limit."""
    key = f"{symbol.upper()}::{period}".strip()
    entry = CACHE_STORE.get(key)
    if not entry:
        return None

    payload = entry.get('payload')
    if payload is None:
        return None

    return copy.deepcopy(payload)


def _put_cache(symbol, period, payload):
    """Cache payloads keyed by symbol and requested period."""
    key = f"{symbol.upper()}::{period}".strip()
    CACHE_STORE[key] = {
        'fetched_at': time.time(),
        'payload': copy.deepcopy(payload),
    }


def _fetch_stock_payload(symbol, period):
    """Single-statement fetch function used by the retry wrapper."""
    stock = yf.Ticker(symbol, session=REQUEST_SESSION)

    period_map = {
        "1 Year": "1y",
        "2 Years": "2y",
        "5 Years": "5y",
        "Custom": "max"
    }

    yf_period = period_map.get(period, "1y")
    data = stock.history(period=yf_period)

    if data.empty:
        return None

    data = calculate_technical_indicators(data)

    return {
        'prices': data,
        'info': stock.info,
        'symbol': symbol.upper()
    }


def get_stock_data(symbol, period):
    """Fetch stock data from yfinance and hydrate the same payload shape expected by dashboard UI code."""
    symbol = (symbol or '').upper()
    period_map = {
        "1 Year": "1y",
        "2 Years": "2y",
        "5 Years": "5y",
        "Custom": "max"
    }
    normalized_period = period_map.get(period, "1y")

    cached_payload = _cache_is_fresh(symbol, normalized_period)
    if cached_payload is not None:
        return cached_payload

    attempts = 0
    while attempts < 4:
        try:
            payload = _fetch_stock_payload(symbol, period)
            if payload is None:
                return None

            _put_cache(symbol, normalized_period, payload)
            return payload

        except YFRateLimitError as e:
            if attempts < 3:
                backoff_seconds = 2 ** attempts
                time.sleep(backoff_seconds)
                attempts += 1
                continue

            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None:
                return stale_payload

            raise requests.exceptions.HTTPError(f"Rate limit exceeded for {symbol}: {type(e).__name__}: {e}")
        except requests.exceptions.Timeout as e:
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None:
                return stale_payload
            raise requests.exceptions.Timeout(f"API timeout while fetching {symbol}: {type(e).__name__}: {e}")
        except requests.exceptions.HTTPError as e:
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None:
                return stale_payload
            raise requests.exceptions.HTTPError(f"Rate limit or API response error while fetching {symbol}: {type(e).__name__}: {e}")
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid symbol {symbol}: {type(e).__name__}: {e}")
        except Exception as e:
            error_type = type(e).__name__
            message = str(e)
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None and ("429" in message or "Too Many Requests" in message or "rate limit" in message.lower()):
                return stale_payload
            if "Invalid symbol" in message or "symbol" in message.lower() and "not found" in message.lower():
                raise ValueError(f"Invalid symbol {symbol}: {error_type}: {message}")
            elif "429" in message or "Too Many Requests" in message or "rate limit" in message.lower():
                raise requests.exceptions.HTTPError(f"Rate limit exceeded for {symbol}: {error_type}: {message}")
            elif "No data" in message or "no data" in message.lower() or "empty" in message.lower():
                raise ValueError(f"No data for range for {symbol}: {error_type}: {message}")
            else:
                raise Exception(f"Fetch failed for {symbol}: {error_type}: {message}")

    return None
