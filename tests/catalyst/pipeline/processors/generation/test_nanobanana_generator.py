# tests/catalyst/pipeline/processors/generation/test_nanobanana_generator.py

import pytest
import json
import base64
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, call, ANY

from catalyst.context import RunContext
from catalyst.pipeline.processors.generation.nanobanana_generator import (
    NanoBananaGeneration,
)
from catalyst import settings
from catalyst.pipeline.processors.generation import (
    nanobanana_generator as generator_module,
)


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    """Provides a fresh RunContext pointing to a temporary results directory."""
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.final_report = {"detailed_key_pieces": [{"key_piece_name": "Test Jacket"}]}
    return context


@pytest.fixture
def prompts_file(run_context: RunContext) -> Path:
    """Creates a mock prompts file with a single valid prompt."""
    prompts_data = {"Test Jacket": {"final_garment": "a test prompt"}}
    prompts_path = run_context.results_dir / settings.PROMPTS_FILENAME
    prompts_path.parent.mkdir(parents=True, exist_ok=True)
    with open(prompts_path, "w") as f:
        json.dump(prompts_data, f)
    return prompts_path


@pytest.fixture
def mock_client(mocker) -> MagicMock:
    """Creates a mock client instance with valid, realistic response data."""
    one_pixel_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    image_bytes = base64.b64decode(one_pixel_png_b64)
    mock_image_data = mocker.Mock(data=image_bytes)
    mock_part = mocker.Mock(inline_data=mock_image_data)
    mock_content = mocker.Mock(parts=[mock_part])
    mock_candidate = mocker.Mock(content=mock_content)
    mock_response = AsyncMock(candidates=[mock_candidate])
    client = MagicMock()
    client.aio.models.generate_content = AsyncMock(return_value=mock_response)
    return client


@pytest.mark.asyncio
class TestNanoBananaGenerationDI:
    """Tests the refactored NanoBananaGeneration using dependency injection."""

    async def test_process_happy_path_with_injected_client(
        self, run_context, prompts_file, mock_client
    ):
        """Verify a successful default run using an injected mock client."""
        generator = NanoBananaGeneration(client=mock_client)
        await generator.process(run_context)

        mock_client.aio.models.generate_content.assert_called_once()
        assert (run_context.results_dir / "test-jacket-t7.png").exists()

    # --- START: THE DEFINITIVE TEST FIX ---
    async def test_process_with_temp_override(
        self, run_context, prompts_file, mock_client
    ):
        """Verify that the temperature override is used correctly."""
        generator = NanoBananaGeneration(client=mock_client)
        # Call the process method with only the temperature override
        await generator.process(run_context, temperature_override=1.5)

        # Assert that the API was called with the correct parameters
        mock_client.aio.models.generate_content.assert_called_once_with(
            model=settings.IMAGE_GENERATION_MODEL_NAME,
            contents=["a test prompt"],
            config=ANY,
        )

        # Verify the temperature was correctly set in the config object
        config_arg = mock_client.aio.models.generate_content.call_args.kwargs["config"]
        assert config_arg.temperature == 1.5

        # Assert that the filename includes the correct suffix
        assert (run_context.results_dir / "test-jacket-t15.png").exists()

    # --- END: THE DEFINITIVE TEST FIX ---

    async def test_process_does_not_create_real_client_if_injected(
        self, run_context, prompts_file, mock_client, mocker
    ):
        """Verify that the real genai.Client is never called when a mock is injected."""
        spy = mocker.spy(generator_module.genai, "Client")
        generator = NanoBananaGeneration(client=mock_client)
        await generator.process(run_context)
        spy.assert_not_called()

    async def test_process_handles_no_api_key_gracefully(self, run_context, mocker):
        """Verify that the generator disables itself if no API key is present."""
        mocker.patch.object(settings, "GEMINI_API_KEY", None)
        spy = mocker.spy(generator_module.genai, "Client")
        generator = NanoBananaGeneration()
        await generator.process(run_context)
        spy.assert_not_called()
