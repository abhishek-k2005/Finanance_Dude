"""
news_fetcher.py
---------------
Fetches recent company news from the Finnhub /company-news endpoint (free tier).

Usage:
    from news_fetcher import fetch_recent_news
    articles = fetch_recent_news("AAPL")
"""

import os
import requests
from datetime import datetime, timedelta, date


FINNHUB_BASE_URL = "https://finnhub.io/api/v1/company-news"


def fetch_recent_news(symbol: str, as_of_date=None, days: int = 5) -> list[dict]:
    """
    Fetch recent news for *symbol* using the Finnhub /company-news endpoint.

    Parameters
    ----------
    symbol      : Stock ticker, e.g. "AAPL".
    as_of_date  : End date (str "YYYY-MM-DD" or datetime/date object).
                  Defaults to today if not provided.
    days        : How many calendar days to look back (default 5).

    Returns
    -------
    List of up to 5 dicts, each with keys:
        headline, summary, source, date, url
    Returns an empty list on any failure — never raises.
    """
    try:
        api_key = os.getenv("FINNHUB_API_KEY", "")
        if not api_key:
            return []

        # Resolve end date
        if as_of_date is None:
            end_dt = date.today()
        elif isinstance(as_of_date, str):
            end_dt = datetime.strptime(as_of_date, "%Y-%m-%d").date()
        elif isinstance(as_of_date, datetime):
            end_dt = as_of_date.date()
        elif isinstance(as_of_date, date):
            end_dt = as_of_date
        else:
            end_dt = date.today()

        start_dt = end_dt - timedelta(days=days)

        params = {
            "symbol": symbol.upper(),
            "from": start_dt.strftime("%Y-%m-%d"),
            "to": end_dt.strftime("%Y-%m-%d"),
            "token": api_key,
        }

        response = requests.get(FINNHUB_BASE_URL, params=params, timeout=10)
        response.raise_for_status()

        raw_articles = response.json()
        if not isinstance(raw_articles, list):
            return []

        results = []
        for article in raw_articles[:5]:
            try:
                # Finnhub returns Unix timestamp in 'datetime' field
                ts = article.get("datetime", 0)
                article_date = (
                    datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
                    if ts
                    else "N/A"
                )
                results.append(
                    {
                        "headline": article.get("headline", "").strip(),
                        "summary": article.get("summary", "").strip(),
                        "source": article.get("source", "").strip(),
                        "date": article_date,
                        "url": article.get("url", "").strip(),
                    }
                )
            except Exception:
                continue  # skip malformed article silently

        return results

    except Exception:
        return []
