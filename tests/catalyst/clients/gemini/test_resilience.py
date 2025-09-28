# tests/catalyst/clients/gemini/test_resilience.py

import pytest
from google.api_core import exceptions as google_exceptions

from catalyst.clients.gemini.resilience import should_retry, calculate_backoff_delay
from catalyst import settings  # Import settings to use the new base delay


class TestGeminiResilience:
    @pytest.mark.parametrize(
        "exception",
        [
            google_exceptions.ServiceUnavailable("Service is down"),
            google_exceptions.TooManyRequests("Rate limit exceeded"),
        ],
    )
    def test_should_retry_on_retryable_errors(self, exception):
        assert should_retry(exception) is True

    @pytest.mark.parametrize(
        "exception",
        [
            google_exceptions.BadRequest("Invalid request"),
            ValueError("A content-level error"),
        ],
    )
    def test_should_not_retry_on_permanent_errors(self, exception):
        assert should_retry(exception) is False

    def test_calculate_backoff_delay_is_exponential_with_jitter(self):
        """Verify the backoff calculation uses the new settings correctly."""
        # --- START: THE DEFINITIVE FIX ---
        # The assertions must now match the new formula: base * (2**attempt) + jitter
        base = settings.RETRY_BACKOFF_BASE_DELAY

        delay1 = calculate_backoff_delay(0)  # base * 1 + jitter
        delay2 = calculate_backoff_delay(1)  # base * 2 + jitter
        delay3 = calculate_backoff_delay(2)  # base * 4 + jitter

        assert (base * 1 + 0.5) <= delay1 <= (base * 1 + 1.5)
        assert (base * 2 + 0.5) <= delay2 <= (base * 2 + 1.5)
        assert (base * 4 + 0.5) <= delay3 <= (base * 4 + 1.5)
        # --- END: THE DEFINITIVE FIX ---
