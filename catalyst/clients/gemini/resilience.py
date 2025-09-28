# catalyst/clients/gemini/resilience.py

"""
Provides low-level, network-focused resilience helpers (retry logic, backoff
delays) for the Gemini API client.
"""

import random
from google.api_core import exceptions as google_exceptions
from ... import settings


def should_retry(e: Exception) -> bool:
    """
    Determines if an API error is transient and purely network-related.

    This function's responsibility is now strictly limited to identifying
    temporary network or server-side issues that are likely to be resolved
    on a subsequent attempt. It no longer handles content-level errors.
    """
    # Check for specific, known-retryable Google API exception types.
    if isinstance(
        e,
        (
            google_exceptions.DeadlineExceeded,  # 504
            google_exceptions.ServiceUnavailable,  # 503
            google_exceptions.TooManyRequests,  # 429
            google_exceptions.InternalServerError,  # 500
            google_exceptions.GatewayTimeout,  # 504
        ),
    ):
        return True

    # As a fallback, check for a common "service unavailable" string.
    if "service unavailable" in str(e).lower():
        return True

    # If none of the above conditions are met, the error is considered
    # a content-level or permanent issue and should not be retried here.
    return False


def calculate_backoff_delay(attempt: int) -> float:
    """
    Calculates exponential backoff delay with jitter, based on the central settings.

    This prevents a "thundering herd" problem where many clients retry at
    the exact same time after a service disruption.
    """
    # --- START: THE DEFINITIVE, CONFIGURABLE REFACTOR ---
    base_delay = settings.RETRY_BACKOFF_BASE_DELAY

    # Exponential backoff: base * 2^0, base * 2^1, base * 2^2, ...
    exponential_delay = base_delay * (2**attempt)

    # Jitter: Add a random value to spread out retries.
    jitter = random.uniform(0.5, 1.5)

    delay = exponential_delay + jitter

    # Cap the delay at a reasonable maximum to prevent excessively long waits.
    return min(delay, 60)
    # --- END: THE DEFINITIVE, CONFIGURABLE REFACTOR ---
