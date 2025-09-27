import pytest
from pydantic import BaseModel
from google.api_core import exceptions as google_exceptions

from catalyst.clients.gemini.core import generate_content_core_async
from catalyst.clients.gemini.schema import process_response_schema


class CoreTestModel(BaseModel):
    name: str


@pytest.mark.asyncio
class TestGeminiCore:
    async def test_generate_content_core_async_success(self, mocker):
        """
        Verify the core function correctly processes the schema, calls the client,
        and returns the raw text.
        """
        prompt = ["A prompt"]
        schema_model = CoreTestModel

        mock_response = mocker.Mock()
        mock_response.text = '{"name": "test"}'

        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            return_value=mock_response,
        )

        result = await generate_content_core_async(
            prompt_parts=prompt,
            response_schema=schema_model,
            tools=None,
            model_name="gemini-pro",
        )

        assert result is not None
        assert result["text"] == '{"name": "test"}'

        mock_generate_content.assert_awaited_once()
        call_kwargs = mock_generate_content.call_args.kwargs

        # --- START: THE DEFINITIVE FIX ---
        # Assert against the attribute of the 'GenerateContentConfig' object.
        expected_schema = process_response_schema(schema_model)
        assert call_kwargs["config"].response_schema == expected_schema
        # --- END: THE DEFINITIVE FIX ---

    async def test_generate_content_core_async_handles_retryable_failure(self, mocker):
        mocker.patch("asyncio.sleep")
        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            side_effect=google_exceptions.ServiceUnavailable("Service is down"),
        )
        from catalyst import settings

        result = await generate_content_core_async([], None, None)

        assert result is None
        assert mock_generate_content.call_count == settings.RETRY_NETWORK_ATTEMPTS

    async def test_generate_content_core_async_handles_permanent_failure(self, mocker):
        mocker.patch("asyncio.sleep")
        mock_generate_content = mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            side_effect=google_exceptions.BadRequest("Invalid request"),
        )

        result = await generate_content_core_async([], None, None)

        assert result is None
        mock_generate_content.assert_called_once()
