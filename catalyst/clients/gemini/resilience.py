# catalyst/clients/gemini/resilience.py

"""
Provides resilience helpers (retry logic, backoff delays) for API clients.
"""

import random


def should_retry(e: Exception) -> bool:
    """Determines if an API error is transient and worth retrying."""
    error_str = str(e).lower()
    retryable_messages = [
        "deadline exceeded",
        "service unavailable",
        "500",
        "503",
        "504",
        "429",  # Rate limiting
    ]
    return any(msg in error_str for msg in retryable_messages)


def calculate_backoff_delay(attempt: int) -> float:
    """Calculates exponential backoff delay with jitter."""
    delay = (2**attempt) + random.uniform(0.5, 1.5)
    return min(delay, 60)  # Cap delay at 60 seconds
