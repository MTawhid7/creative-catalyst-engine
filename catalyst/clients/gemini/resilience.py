# catalyst/clients/gemini/resilience.py

"""
Provides resilience helpers (retry logic, backoff delays) for API clients.
"""

import random


def should_retry(e: Exception) -> bool:
    """
    Determines if an API error is transient and worth retrying. This now
    includes handling empty responses as a retryable condition.
    """
    error_str = str(e).lower()

    # --- START OF DEFINITIVE FIX ---
    # Add "empty response object" to the list of retryable transient errors.
    # This makes the entire client more robust against API flakiness or
    # safety-filter-induced empty returns.
    retryable_messages = [
        "deadline exceeded",
        "service unavailable",
        "500",
        "503",
        "504",
        "429",  # Rate limiting
        "api call returned an empty response object",  # The critical addition
    ]
    # --- END OF DEFINITIVE FIX ---

    return any(msg in error_str for msg in retryable_messages)


def calculate_backoff_delay(attempt: int) -> float:
    """Calculates exponential backoff delay with jitter."""
    delay = (2**attempt) + random.uniform(0.5, 1.5)
    return min(delay, 60)  # Cap delay at 60 seconds
