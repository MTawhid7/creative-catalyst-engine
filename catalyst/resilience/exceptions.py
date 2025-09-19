# catalyst/resilience/exceptions.py

"""Custom exceptions for the resilience invoker."""


class ResilienceError(Exception):
    """Base exception for a permanent failure within the resilience invoker."""

    pass


class MaxRetriesExceededError(ResilienceError):
    """Raised when the invoker fails after all retry attempts."""

    def __init__(self, last_exception: Exception):
        self.last_exception = last_exception
        super().__init__(
            f"API call failed after all retries. Last error: {last_exception}"
        )
