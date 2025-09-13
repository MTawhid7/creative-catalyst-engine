# catalyst/clients/gemini/resilience.py

"""
Provides resilience helpers (retry logic, backoff delays) for API clients.
This version is enhanced to be more robust by checking for specific, structured
exception types in addition to string matching.
"""

import random
from google.api_core import exceptions as google_exceptions


def should_retry(e: Exception) -> bool:
    """
    Determines if an API error is transient and worth retrying.

    This function checks for both specific exception types from the Google API
    client library and common transient error messages. This provides a more
    robust and future-proof way to handle retryable conditions.
    """
    # --- START: ROBUST EXCEPTION CHECKING REFACTOR ---

    # 1. Check for specific, known-retryable exception types first.
    # This is the most robust method.
    if isinstance(
        e,
        (
            google_exceptions.DeadlineExceeded,
            google_exceptions.ServiceUnavailable,
            google_exceptions.TooManyRequests,  # Handles 429 errors
            google_exceptions.InternalServerError,  # Handles 500 errors
            google_exceptions.GatewayTimeout,  # Handles 504 errors
        ),
    ):
        return True

    # 2. As a fallback, check for common error message strings.
    # This catches errors that might not have a specific type, like our
    # custom "empty response" error.
    error_str = str(e).lower()
    retryable_messages = [
        "service unavailable",  # A common fallback message for 503
        "api call returned an empty response object",
    ]

    if any(msg in error_str for msg in retryable_messages):
        return True

    # --- END: ROBUST EXCEPTION CHECKING REFACTOR ---

    # If none of the above conditions are met, the error is not retryable.
    return False


def calculate_backoff_delay(attempt: int) -> float:
    """
    Calculates exponential backoff delay with jitter.

    This prevents a "thundering herd" problem where many clients retry at
    the exact same time after a service disruption.
    """
    # Exponential backoff: 2^0, 2^1, 2^2, ...
    base_delay = 2**attempt
    # Jitter: Add a random value to spread out retries.
    jitter = random.uniform(0.5, 1.5)

    delay = base_delay + jitter

    # Cap the delay at a reasonable maximum (e.g., 60 seconds).
    return min(delay, 60)
