"""Phase 2 observability: groundedness checks and session caching."""

import time
import json
from typing import Any, Dict, List, Optional
from observability import extract_numbers_from_text, log_event


class SessionCache:
    """Session-scoped cache with per-(symbol, timeframe, query-type) keys and TTL."""

    def __init__(self, ttl_seconds: int = 600):
        """
        Initialize session cache.
        Args:
            ttl_seconds: Time-to-live for cache entries (default 10 min)
        """
        self.ttl_seconds = ttl_seconds
        self.store: Dict[tuple, Dict[str, Any]] = {}

    def _make_key(self, key_tuple: tuple) -> tuple:
        """Normalize cache key tuple."""
        if isinstance(key_tuple, tuple) and len(key_tuple) == 3:
            symbol, timeframe, query_type = key_tuple
            return (symbol.upper(), timeframe, query_type)
        return key_tuple

    def get(self, key: tuple) -> Optional[Any]:
        """Retrieve cached value if fresh (within TTL)."""
        key = self._make_key(key)
        entry = self.store.get(key)

        if entry is None:
            return None

        now = time.time()
        age = now - entry['fetched_at']

        if age > self.ttl_seconds:
            del self.store[key]
            return None

        return entry['payload']

    def set(self, key: tuple, payload: Any) -> None:
        """Store value in cache with current timestamp."""
        key = self._make_key(key)
        self.store[key] = {
            'fetched_at': time.time(),
            'payload': payload
        }

    def clear(self) -> None:
        """Clear entire cache (e.g., session end)."""
        self.store.clear()


def groundedness_check(llm_response: str, tool_result: Dict[str, Any], query: str) -> List[Dict[str, Any]]:
    """
    Verify that numbers stated in LLM response exist in the tool result.
    Returns list of mismatches (empty list if groundedness passes).
    Each mismatch is a dict with: mismatched_value, type, query, grounding_keys
    """
    extracted_numbers = extract_numbers_from_text(llm_response)

    tool_text = json.dumps(tool_result, default=str)
    tool_numbers = extract_numbers_from_text(tool_text)
    tool_values = {n['value'] for n in tool_numbers}

    mismatches = []
    for number in extracted_numbers:
        found = False
        for tv in tool_values:
            if abs(number['value'] - tv) < 0.01:
                found = True
                break
        if not found:
            mismatches.append({
                "mismatched_value": number['text'],
                "type": number['type'],
                "query": query,
                "grounding_keys": list(tool_result.keys()) if isinstance(tool_result, dict) else []
            })

    return mismatches
