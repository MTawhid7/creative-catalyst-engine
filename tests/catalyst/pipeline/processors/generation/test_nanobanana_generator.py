# tests/catalyst/pipeline/processors/generation/test_nanobanana_generator.py

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

from catalyst.context import RunContext
from catalyst.pipeline.processors.generation.nanobanana_generator import (
    NanoBananaGeneration,
)
from catalyst import settings

# Define paths to the clients and classes we need to mock
GENAI_CLIENT_PATH = (
    "catalyst.pipeline.processors.generation.nanobanana_generator.genai.Client"
)
# --- START: THE FIX (Step 1) ---
# We only need to mock Image.open. We will check the 'save' method on the object it returns.
IMAGE_OPEN_PATH = (
    "catalyst.pipeline.processors.generation.nanobanana_generator.Image.open"
)
# --- END: THE FIX (Step 1) ---


@pytest.fixture
def mock_run_context(tmp_path: Path) -> RunContext:
    """Provides a RunContext with a dummy final_report and a results directory."""
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.final_report = {
        "detailed_key_pieces": [
            {"key_piece_name": "The Test Blazer"},
            {"key_piece_name": "Another Piece"},
        ]
    }
    (tmp_path / context.run_id).mkdir()
    context.results_dir = tmp_path / context.run_id
    return context


@pytest.fixture
def populated_run_context(mock_run_context: RunContext) -> RunContext:
    """Provides a RunContext where a fake prompts.json file already exists."""
    prompts_data = {
        "The Test Blazer": {
            "mood_board": "A mood board for the test blazer.",
            "final_garment": "A final image of the test blazer.",
        }
    }
    prompts_path = mock_run_context.results_dir / settings.PROMPTS_FILENAME
    with open(prompts_path, "w") as f:
        json.dump(prompts_data, f)
    return mock_run_context


@pytest.mark.asyncio
async def test_nanobanana_generator_happy_path(mocker, populated_run_context):
    """
    Tests the full success path: prompts are read, AI is called, images are saved,
    and the report is updated with the new paths.
    """
    # ARRANGE
    mock_gemini_client_instance = MagicMock()
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_part.inline_data.data = b"fake_image_bytes"
    mock_response.candidates = [MagicMock(content=MagicMock(parts=[mock_part]))]
    mock_gemini_client_instance.aio.models.generate_content = AsyncMock(
        return_value=mock_response
    )
    mocker.patch(GENAI_CLIENT_PATH, return_value=mock_gemini_client_instance)

    # --- START: THE FIX (Step 2) ---
    # Mock Image.open and get a handle to the mock object it returns.
    mock_image_open = mocker.patch(IMAGE_OPEN_PATH)
    # The object that Image.open() returns is also a mock. This represents the 'image' variable.
    mock_image_instance = mock_image_open.return_value
    # --- END: THE FIX (Step 2) ---

    processor = NanoBananaGeneration()

    # ACT
    context = await processor.process(populated_run_context)

    # ASSERT
    assert mock_gemini_client_instance.aio.models.generate_content.call_count == 2

    # --- START: THE FIX (Step 3) ---
    # Assert that the 'save' method on the returned mock instance was called twice.
    assert mock_image_instance.save.call_count == 2
    # --- END: THE FIX (Step 3) ---

    updated_piece = context.final_report["detailed_key_pieces"][0]
    assert "final_garment_relative_path" in updated_piece
    assert "mood_board_relative_path" in updated_piece
    assert updated_piece["final_garment_relative_path"].endswith(".png")
    assert "the-test-blazer" in updated_piece["final_garment_relative_path"]


@pytest.mark.asyncio
async def test_nanobanana_generator_no_prompts_file(mocker, mock_run_context):
    """
    Tests that if prompts.json is missing, no AI calls are made and the
    processor exits gracefully.
    """
    # ARRANGE
    mock_gemini_client_instance = MagicMock()
    mock_gemini_client_instance.aio.models.generate_content = AsyncMock()
    mocker.patch(GENAI_CLIENT_PATH, return_value=mock_gemini_client_instance)

    processor = NanoBananaGeneration()

    # ACT
    await processor.process(mock_run_context)

    # ASSERT
    mock_gemini_client_instance.aio.models.generate_content.assert_not_called()
