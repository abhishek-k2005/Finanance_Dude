import time
import json
from typing import Any, Dict, Optional, Tuple
from functools import wraps
from observability import log_event


class SessionCache:
    """Session-scoped cache with per-(symbol, timeframe, query-type) keys and TTL."""

    def __init__(self, ttl_seconds: int = 600):
        """
        Initialize session cache.
        Args:
            ttl_seconds: Time-to-live for cache entries (default 10 min)
        """
        self.ttl_seconds = ttl_seconds
        self.store: Dict[str, Dict[str, Any]] = {}

    def _make_key(self, symbol: str, timeframe: str, query_type: str) -> str:
        """Generate cache key from symbol, timeframe, and query type."""
        return f"{symbol.upper()}::{timeframe}::{query_type}".strip()

    def get(self, symbol: str, timeframe: str, query_type: str) -> Optional[Any]:
        """
        Retrieve cached value if fresh (within TTL).
        Returns None if expired or not found.
        """
        key = self._make_key(symbol, timeframe, query_type)
        entry = self.store.get(key)

        if entry is None:
            log_event(
                "cache_miss",
                key=key,
                symbol=symbol,
                timeframe=timeframe,
                query_type=query_type
            )
            return None

        now = time.time()
        age = now - entry['fetched_at']

        if age > self.ttl_seconds:
            del self.store[key]
            log_event(
                "cache_expired",
                key=key,
                age_seconds=age,
                ttl_seconds=self.ttl_seconds
            )
            return None

        log_event(
            "cache_hit",
            key=key,
            symbol=symbol,
            timeframe=timeframe,
            query_type=query_type,
            age_seconds=round(age, 2)
        )
        return entry['payload']

    def put(self, symbol: str, timeframe: str, query_type: str, payload: Any) -> None:
        """Store value in cache with current timestamp."""
        key = self._make_key(symbol, timeframe, query_type)
        self.store[key] = {
            'fetched_at': time.time(),
            'payload': payload,
            'size_bytes': len(json.dumps(payload, default=str).encode('utf-8'))
        }
        log_event(
            "cache_store",
            key=key,
            symbol=symbol,
            timeframe=timeframe,
            query_type=query_type,
            size_bytes=self.store[key]['size_bytes']
        )

    def clear(self) -> None:
        """Clear entire cache (e.g., session end)."""
        size = len(self.store)
        self.store.clear()
        log_event(
            "cache_cleared",
            entries_cleared=size
        )

    def stats(self) -> Dict[str, Any]:
        """Return cache statistics."""
        total_size = sum(e.get('size_bytes', 0) for e in self.store.values())
        return {
            'entries': len(self.store),
            'total_size_bytes': total_size,
            'ttl_seconds': self.ttl_seconds,
            'keys': list(self.store.keys())
        }


def cache_result(cache_instance: SessionCache, query_type: str):
    """
    Decorator to cache tool/data-fetch results by (symbol, timeframe, query_type).
    Usage:
        @cache_result(session_cache, "stock_data")
        def get_stock_data(symbol: str, timeframe: str):
            ...
    """
    def decorator(func):
        @wraps(func)
        def wrapper(symbol: str, timeframe: str, *args, **kwargs):
            cached = cache_instance.get(symbol, timeframe, query_type)
            if cached is not None:
                return cached

            result = func(symbol, timeframe, *args, **kwargs)
            cache_instance.put(symbol, timeframe, query_type, result)
            return result

        return wrapper

    return decorator


global_session_cache = SessionCache(ttl_seconds=600)
