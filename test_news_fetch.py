"""Test fetch_recent_news output for AAPL."""
import json
from news_fetcher import fetch_recent_news

articles = fetch_recent_news("AAPL")
print(f"Fetched {len(articles)} articles\n")
for i, a in enumerate(articles, 1):
    print(f"[{i}] {a['date']} | {a['source']}")
    print(f"    HEADLINE : {a['headline']}")
    print(f"    SUMMARY  : {a['summary'][:120]}..." if len(a['summary']) > 120 else f"    SUMMARY  : {a['summary']}")
    print(f"    URL      : {a['url']}")
    print()
