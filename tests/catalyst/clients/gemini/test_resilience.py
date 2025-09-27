# tests/catalyst/clients/gemini/test_resilience.py

import pytest
from google.api_core import exceptions as google_exceptions

from catalyst.clients.gemini.resilience import should_retry, calculate_backoff_delay


class TestGeminiResilience:
    @pytest.mark.parametrize(
        "exception",
        [
            google_exceptions.ServiceUnavailable("Service is down"),
            google_exceptions.TooManyRequests("Rate limit exceeded"),
            google_exceptions.InternalServerError("Internal error"),
            Exception("A generic service unavailable error"),
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
        delay1 = calculate_backoff_delay(0)  # 2**0 + jitter
        delay2 = calculate_backoff_delay(1)  # 2**1 + jitter
        delay3 = calculate_backoff_delay(2)  # 2**2 + jitter

        assert 1.5 <= delay1 <= 2.5
        assert 2.5 <= delay2 <= 3.5
        assert 4.5 <= delay3 <= 5.5
