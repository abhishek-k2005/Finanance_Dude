import json
import time
import logging
import re
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)

logger = logging.getLogger(__name__)


def log_event(event_type: str, **kwargs) -> None:
    """Log a structured JSON event."""
    event = {
        "timestamp": datetime.utcnow().isoformat(),
        "event_type": event_type,
        **kwargs
    }
    logger.info(json.dumps(event, default=str))


def trace_llm_call(func: Callable) -> Callable:
    """Decorator to trace LLM calls: measure latency, input/output size, cost."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        input_text = str(args) + str(kwargs)
        input_size = len(input_text.encode('utf-8'))

        result = func(*args, **kwargs)

        latency = time.time() - start_time
        output_text = str(result)
        output_size = len(output_text.encode('utf-8'))

        estimated_cost = (input_size + output_size) * 0.0001

        log_event(
            "llm_call",
            function=func.__name__,
            input_size_bytes=input_size,
            output_size_bytes=output_size,
            latency_seconds=round(latency, 3),
            estimated_cost_usd=round(estimated_cost, 6),
            status="success"
        )

        return result

    return wrapper


def trace_tool_call(func: Callable) -> Callable:
    """Decorator to trace tool/data-fetch calls: measure latency, cost, size."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()

        input_text = str(args) + str(kwargs)
        input_size = len(input_text.encode('utf-8'))

        try:
            result = func(*args, **kwargs)
            status = "success"
            error = None
        except Exception as e:
            status = "error"
            error = str(e)
            result = None

        latency = time.time() - start_time
        output_text = str(result) if result else ""
        output_size = len(output_text.encode('utf-8'))

        estimated_cost = (input_size + output_size) * 0.00005

        log_event(
            "tool_call",
            function=func.__name__,
            input_size_bytes=input_size,
            output_size_bytes=output_size,
            latency_seconds=round(latency, 3),
            estimated_cost_usd=round(estimated_cost, 6),
            status=status,
            error=error
        )

        if error:
            raise Exception(error)

        return result

    return wrapper


def extract_numbers_from_text(text: str) -> List[Dict[str, Any]]:
    """
    Extract monetary values, percentages, and numeric values from text.
    Handles formatted numbers: $4561.70B, 16.4M, +0.16 (+0.05%), 35.85
    """
    if not text:
        return []

    numbers = []

    formatted_currency_pattern = r'\$[\d,]+\.?\d*\s*[BKM]?'
    for match in re.finditer(formatted_currency_pattern, text):
        value_str = match.group().replace('$', '').replace(',', '').strip()
        multiplier = 1
        if value_str and value_str[-1].upper() in ['B', 'K', 'M']:
            multiplier_char = value_str[-1].upper()
            value_str = value_str[:-1]
            if multiplier_char == 'B':
                multiplier = 1e9
            elif multiplier_char == 'M':
                multiplier = 1e6
            elif multiplier_char == 'K':
                multiplier = 1e3
        try:
            value = float(value_str) * multiplier
            numbers.append({
                "type": "currency",
                "value": value,
                "text": match.group(),
                "position": match.start()
            })
        except ValueError:
            pass

    percent_pattern = r'([+-]?\d+\.?\d*)\s*%'
    for match in re.finditer(percent_pattern, text):
        try:
            value = float(match.group(1))
            numbers.append({
                "type": "percentage",
                "value": value,
                "text": match.group(),
                "position": match.start()
            })
        except ValueError:
            pass

    formatted_number_pattern = r'([+-]?\d+\.?\d*)\s*[BKM](?!\w)'
    for match in re.finditer(formatted_number_pattern, text):
        value_str = match.group(1)
        multiplier_char = match.group(0)[-1].upper()
        multiplier = 1
        if multiplier_char == 'B':
            multiplier = 1e9
        elif multiplier_char == 'M':
            multiplier = 1e6
        elif multiplier_char == 'K':
            multiplier = 1e3
        try:
            value = float(value_str) * multiplier
            if not any(n['value'] == value for n in numbers):
                numbers.append({
                    "type": "numeric",
                    "value": value,
                    "text": match.group(),
                    "position": match.start()
                })
        except ValueError:
            pass

    plain_numeric_pattern = r'([+-]?\d+\.?\d*(?:[eE][+-]?\d+)?)'
    for match in re.finditer(plain_numeric_pattern, text):
        try:
            value = float(match.group(1))
            if value > 0 and not any(abs(n['value'] - value) < 0.0001 for n in numbers):
                numbers.append({
                    "type": "numeric",
                    "value": value,
                    "text": match.group(),
                    "position": match.start()
                })
        except ValueError:
            pass

    return numbers


def check_groundedness(llm_response: str, grounding_data: Dict[str, Any], query: str) -> Dict[str, Any]:
    """
    Verify that numbers stated in LLM response exist in the grounding data.
    Mismatch behavior is LOG-ONLY (non-blocking).
    """
    extracted_numbers = extract_numbers_from_text(llm_response)

    grounding_text = json.dumps(grounding_data, default=str)
    grounding_numbers = extract_numbers_from_text(grounding_text)
    grounding_values = {n['value'] for n in grounding_numbers}

    mismatches = []
    for number in extracted_numbers:
        found = False
        for gv in grounding_values:
            if abs(number['value'] - gv) < 0.01:
                found = True
                break
        if not found:
            mismatches.append({
                "stated_value": number['value'],
                "type": number['type'],
                "text": number['text']
            })

    if mismatches:
        log_event(
            "groundedness_check_failed",
            query=query,
            mismatches=mismatches,
            llm_response_length=len(llm_response),
            grounding_data_keys=list(grounding_data.keys()) if isinstance(grounding_data, dict) else None,
            note="Non-blocking: logged for observability only"
        )
    else:
        log_event(
            "groundedness_check_passed",
            query=query,
            numbers_verified=len(extracted_numbers)
        )

    return {
        "passed": len(mismatches) == 0,
        "mismatches": mismatches,
        "verified_numbers": len(extracted_numbers) - len(mismatches),
        "blocking": False
    }
