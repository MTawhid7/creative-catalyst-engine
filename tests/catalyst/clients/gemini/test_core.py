# tests/catalyst/clients/gemini/test_core.py

import pytest
from pydantic import BaseModel
from google.api_core import exceptions as google_exceptions

from catalyst.clients.gemini.core import generate_content_core_async
from catalyst.clients.gemini.schema import process_response_schema
from catalyst import settings  # Import settings for the retry count


class CoreTestModel(BaseModel):
    name: str


@pytest.mark.asyncio
class TestGeminiCore:
    async def test_generate_content_core_async_success(self, mocker):
        """
        Verify the core function correctly processes the schema, calls the client,
        and returns the raw text.
        """
        mock_response = mocker.Mock()
        mock_response.text = '{"name": "test"}'

        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            return_value=mock_response,
        )

        result = await generate_content_core_async(
            [], CoreTestModel, None, "gemini-pro"
        )

        assert result is not None
        assert result["text"] == '{"name": "test"}'

        call_kwargs = mock_generate_content.call_args.kwargs
        expected_schema = process_response_schema(CoreTestModel)
        assert call_kwargs["config"].response_schema == expected_schema

    async def test_generate_content_core_async_handles_retryable_failure(self, mocker):
        """
        Verify that the model-failover logic is correctly triggered and that both
        models are retried the configured number of times.
        """
        mocker.patch("asyncio.sleep")
        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            side_effect=google_exceptions.ServiceUnavailable("Service is down"),
        )

        result = await generate_content_core_async([], None, None)

        assert result is None
        # --- START: THE DEFINITIVE FIX ---
        # It should retry 3 times on the primary model, then failover and retry 3 times on the fallback.
        total_expected_calls = settings.MODEL_RETRY_ATTEMPTS * 2
        assert mock_generate_content.call_count == total_expected_calls
        # --- END: THE DEFINITIVE FIX ---

    async def test_generate_content_core_async_handles_permanent_failure(self, mocker):
        """
        Verify that the client fails over but does NOT retry on permanent errors.
        """
        mocker.patch("asyncio.sleep")
        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            side_effect=google_exceptions.BadRequest("Invalid request"),
        )

        result = await generate_content_core_async([], None, None)

        assert result is None
        # --- START: THE DEFINITIVE FIX ---
        # It should be called exactly twice: once for the primary model (which fails),
        # and once for the fallback model (which also fails).
        assert mock_generate_content.call_count == 2
        # --- END: THE DEFINITIVE FIX ---
