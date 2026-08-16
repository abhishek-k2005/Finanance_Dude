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
    """yfinance fetch — used as fallback when Finnhub is unavailable."""
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
        'symbol': symbol.upper(),
        'source': 'yfinance',
    }


def _fetch_finnhub_payload(symbol, period):
    """
    Primary data source: Finnhub /quote + /stock/profile2 + /stock/metric
                         (fundamentals/info) + yfinance history (OHLCV prices).

    Finnhub free tier does NOT include /stock/candle, so full price history
    is always fetched from yfinance.  The info dict (P/E, market-cap, beta,
    52-week range, etc.) still comes exclusively from Finnhub so it remains
    accurate and fast.

    Returns None if FINNHUB_API_KEY is absent or the symbol is unknown.
    Never raises — callers treat None as "source unavailable".
    """
    import os

    api_key = os.getenv("FINNHUB_API_KEY", "")
    if not api_key:
        return None

    try:
        base = "https://finnhub.io/api/v1"
        params = {"symbol": symbol.upper(), "token": api_key}

        # ── 1. Current quote (validates the symbol and gets today's snapshot) ──
        q_resp = requests.get(f"{base}/quote", params=params, timeout=8)
        q_resp.raise_for_status()
        q = q_resp.json()

        # Finnhub returns {} or {c: 0, ...} for unknown symbols
        current_price = q.get("c")
        if not current_price:          # 0, None, or absent = symbol unknown
            return None

        # ── 2. Company profile (name, sector, exchange, etc.) ──────────────────
        p_resp = requests.get(f"{base}/stock/profile2", params=params, timeout=8)
        p_resp.raise_for_status()
        p = p_resp.json()

        # ── 3. Fundamental metrics (P/E, 52-week range, beta, dividend) ────────
        # Best-effort — never blocks the payload if it fails.
        metric_params = {"symbol": symbol.upper(), "token": api_key, "metric": "all"}
        m: dict = {}
        try:
            m_resp = requests.get(f"{base}/stock/metric", params=metric_params, timeout=8)
            if m_resp.status_code == 200:
                m = m_resp.json().get("metric", {}) or {}
        except Exception:
            pass

        # ── Helpers ────────────────────────────────────────────────────────────
        def _safe_float(val):
            """Return float(val) or None — never raises."""
            try:
                return float(val) if val is not None else None
            except (TypeError, ValueError):
                return None

        # ── Build info dict (mirrors yfinance .info shape) ─────────────────────
        mktcap_millions = p.get("marketCapitalization") or 0
        volume_val = _safe_float(m.get("10DayAverageTradingVolume"))
        volume_int = int(volume_val * 1_000_000) if volume_val else 0

        info = {
            "longName":          p.get("name", symbol.upper()),
            "sector":            p.get("finnhubIndustry", "N/A"),
            "industry":          p.get("finnhubIndustry", "N/A"),
            "exchange":          p.get("exchange", "N/A"),
            "currency":          p.get("currency", "USD"),
            "country":           p.get("country", "N/A"),
            "currentPrice":      current_price,
            "previousClose":     _safe_float(q.get("pc")),
            "open":              _safe_float(q.get("o")),
            "dayHigh":           _safe_float(q.get("h")),
            "dayLow":            _safe_float(q.get("l")),
            "regularMarketChange":        _safe_float(q.get("d")),
            "regularMarketChangePercent": _safe_float(q.get("dp")),
            "marketCap": int(mktcap_millions * 1_000_000) if mktcap_millions else None,
            "trailingPE":        _safe_float(m.get("peNormalizedAnnual")),
            "fiftyTwoWeekHigh":  _safe_float(m.get("52WeekHigh")),
            "fiftyTwoWeekLow":   _safe_float(m.get("52WeekLow")),
            "beta":              _safe_float(m.get("beta")),
            "dividendYield":     _safe_float(m.get("dividendYieldIndicatedAnnual")),
        }

        # ── 4. Historical OHLCV — yfinance (Finnhub /stock/candle requires paid tier) ─
        # yfinance is used for the full price time series; Finnhub supplies
        # the info dict above so fundamentals (P/E, beta, etc.) stay accurate.
        yf_period_map = {
            "1 Year": "1y", "2 Years": "2y",
            "5 Years": "5y", "Custom": "max",
        }
        yf_period = yf_period_map.get(period, "1y")
        prices = None
        try:
            stock_yf = yf.Ticker(symbol, session=REQUEST_SESSION)
            prices = stock_yf.history(period=yf_period)
            if not prices.empty:
                prices = calculate_technical_indicators(prices)
            else:
                prices = None
        except Exception:
            prices = None

        # Last-resort single-row snapshot (should never be reached in practice)
        if prices is None or prices.empty:
            ts = q.get("t")
            idx = pd.to_datetime(ts, unit="s", utc=True) if ts else pd.Timestamp.utcnow()
            prices = pd.DataFrame(
                {"Open": [current_price], "High": [current_price],
                 "Low": [current_price], "Close": [current_price],
                 "Volume": [volume_int]},
                index=pd.DatetimeIndex([idx], name="Date"),
            )

        return {
            "prices": prices,
            "info":   info,
            "symbol": symbol.upper(),
            "source": "finnhub",
        }

    except Exception:
        return None


# Errors that are transient and safe to retry (rate-limits, network blips).
_TRANSIENT_EXCEPTIONS = (
    YFRateLimitError,
    requests.exceptions.Timeout,
    requests.exceptions.ConnectionError,
)


def get_stock_data(symbol, period):
    """
    Fetch stock data and hydrate the payload shape expected by dashboard UI code.

    Source priority:
      1. Finnhub /quote + /stock/profile2  (fast, reliable, no auth issues)
      2. yfinance                           (full OHLCV history; rate-limited)

    The returned payload always contains a 'source' key ('finnhub' | 'yfinance').
    Both sources are wrapped by the same 5-minute cache and retry logic.
    """
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

    max_retries = 3
    base_backoff = 5          # seconds; doubles each attempt: 5 → 10 → 20
    last_exc = None

    for attempt in range(max_retries + 1):   # attempt: 0, 1, 2, 3
        try:
            # ── Primary: Finnhub (fast, no per-IP auth issues) ──────────────
            payload = _fetch_finnhub_payload(symbol, period)
            if payload is not None:
                _put_cache(symbol, normalized_period, payload)
                return payload

            # ── Fallback: yfinance (full OHLCV history) ──────────────────────
            payload = _fetch_stock_payload(symbol, period)
            if payload is None:
                return None
            _put_cache(symbol, normalized_period, payload)
            return payload

        except _TRANSIENT_EXCEPTIONS as e:
            last_exc = e
            if attempt < max_retries:
                backoff_seconds = base_backoff * (2 ** attempt)  # 5, 10, 20
                time.sleep(backoff_seconds)
                continue  # retry

            # All retries exhausted — serve stale cache before raising.
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None:
                return stale_payload
            raise requests.exceptions.HTTPError(
                f"Transient error after {max_retries} retries for {symbol}: "
                f"{type(last_exc).__name__}: {last_exc}"
            )

        except requests.exceptions.HTTPError as e:
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None:
                return stale_payload
            raise requests.exceptions.HTTPError(
                f"Rate limit or API response error while fetching {symbol}: {type(e).__name__}: {e}"
            )

        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid symbol {symbol}: {type(e).__name__}: {e}")

        except Exception as e:
            error_type = type(e).__name__
            message = str(e)
            stale_payload = _get_stale_cache(symbol, normalized_period)
            if stale_payload is not None and (
                "429" in message or "Too Many Requests" in message or "rate limit" in message.lower()
            ):
                return stale_payload
            if "Invalid symbol" in message or (
                "symbol" in message.lower() and "not found" in message.lower()
            ):
                raise ValueError(f"Invalid symbol {symbol}: {error_type}: {message}")
            elif "429" in message or "Too Many Requests" in message or "rate limit" in message.lower():
                raise requests.exceptions.HTTPError(
                    f"Rate limit exceeded for {symbol}: {error_type}: {message}"
                )
            elif "No data" in message or "no data" in message.lower() or "empty" in message.lower():
                raise ValueError(f"No data for range for {symbol}: {error_type}: {message}")
            else:
                raise Exception(f"Fetch failed for {symbol}: {error_type}: {message}")
