# tests/catalyst/pipeline/processors/test_synthesis_processors.py

import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path

from catalyst.context import RunContext
from catalyst.pipeline.processors.synthesis import (
    WebResearchProcessor,
    ContextStructuringProcessor,
)

# This is the path to the Gemini client we will be mocking.
GEMINI_CLIENT_PATH = (
    "catalyst.pipeline.processors.synthesis.gemini.generate_content_async"
)


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    """Provides a fresh RunContext, pre-filled with an enriched brief."""
    context = RunContext(user_passage="A test passage", results_dir=tmp_path)
    context.enriched_brief = {"theme_hint": "Test Theme"}
    context.brand_ethos = "Test Ethos"
    context.antagonist_synthesis = "Test Synthesis"
    return context


@pytest.mark.asyncio
async def test_web_research_happy_path(mocker, run_context):
    """
    Tests that WebResearchProcessor successfully gets valid research content
    and stores it in the context.
    """
    # ARRANGE
    mock_gemini = mocker.patch(GEMINI_CLIENT_PATH)
    valid_research_text = "<overarching_theme>Some research.</overarching_theme><key_garments>A test jacket.</key_garments>"
    mock_gemini.return_value = {"text": valid_research_text}

    processor = WebResearchProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    mock_gemini.assert_called_once()
    assert context.raw_research_context == valid_research_text


@pytest.mark.asyncio
async def test_web_research_triggers_self_repair(mocker, run_context):
    """
    Tests the most important feature: if the AI returns research missing the
    'KEY GARMENTS' heading, a second AI call is made to repair it.
    """
    # ARRANGE
    mock_gemini = mocker.patch(GEMINI_CLIENT_PATH)
    flawed_research = "<overarching_theme>This is missing the key garments section.</overarching_theme>"
    repaired_research = "<overarching_theme>This is fixed.</overarching_theme><key_garments>A test jacket.</key_garments>"
    mock_gemini.side_effect = [{"text": flawed_research}, {"text": repaired_research}]

    processor = WebResearchProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    # 1. Assert that the AI was called TWICE.
    assert mock_gemini.call_count == 2

    # --- START: THE DEFINITIVE FIX ---
    # 2. Assert that the second call used the repair prompt.
    # We inspect the keyword arguments (`call.kwargs`) now, not positional args.
    repair_prompt_was_called = False
    for call in mock_gemini.call_args_list:
        # Get the 'prompt_parts' from the keyword arguments dictionary.
        prompt_parts_list = call.kwargs.get("prompt_parts", [])
        if prompt_parts_list:
            prompt_text = prompt_parts_list[0]
            if "repair a provided research document" in prompt_text:
                repair_prompt_was_called = True
                break

    assert (
        repair_prompt_was_called
    ), "The repair prompt was not found in any of the AI calls."
    # --- END: THE DEFINITIVE FIX ---

    # 3. Assert that the final context has the REPAIRED text.
    assert context.raw_research_context == repaired_research


@pytest.mark.asyncio
async def test_web_research_handles_complete_failure(mocker, run_context):
    """
    Tests that if the AI fails to return any content after all retries,
    the processor sets the context to an empty string and does not crash.
    """
    # ARRANGE
    mock_gemini = mocker.patch(GEMINI_CLIENT_PATH, return_value=None)
    # Patch the settings to reduce test time, simulating only 2 retries.
    mocker.patch(
        "catalyst.pipeline.processors.synthesis.settings.TEXT_PROCESSOR_MAX_RETRIES", 2
    )

    processor = WebResearchProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    assert mock_gemini.call_count == 2
    assert context.raw_research_context == ""


@pytest.mark.asyncio
async def test_context_structuring_happy_path(mocker, run_context):
    """
    Tests that the ContextStructuringProcessor correctly takes raw research
    and stores the AI's structured version.
    """
    # ARRANGE
    mock_gemini = mocker.patch(GEMINI_CLIENT_PATH)
    structured_text = "**Key Piece 1 Name:** Test Jacket"
    mock_gemini.return_value = {"text": structured_text}

    # Pre-populate the context with raw research from a previous step.
    run_context.raw_research_context = "Some raw text"
    processor = ContextStructuringProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    mock_gemini.assert_called_once()
    assert context.structured_research_context == structured_text
