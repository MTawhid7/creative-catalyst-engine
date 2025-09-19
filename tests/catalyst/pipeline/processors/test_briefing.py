# tests/catalyst/pipeline/processors/test_briefing.py

import pytest
from unittest.mock import patch, ANY
from pathlib import Path  # <-- Import Path for type hinting

from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError
from catalyst.pipeline.processors.briefing import (
    BriefDeconstructionProcessor,
    EthosClarificationProcessor,
    BriefEnrichmentProcessor,
    StructuredBriefModel,
    EthosModel,
    ConceptsModel,
    AntagonistSynthesisModel,
    KeywordsModel,
)

# This is the path to the function we will mock in all tests.
INVOKER_PATH = "catalyst.pipeline.processors.briefing.invoke_with_resilience"


# --- START: THE FIX ---
@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    """Provides a fresh RunContext for each test."""
    # `tmp_path` is a pytest fixture that provides a unique temporary directory
    # (as a Path object) for each test run.
    return RunContext(
        user_passage="A test passage about minimalist jackets.", results_dir=tmp_path
    )


# --- END: THE FIX ---


@pytest.mark.asyncio
async def test_brief_deconstruction_happy_path(mocker, run_context):
    """
    Tests that BriefDeconstructionProcessor successfully processes a valid AI response,
    applies defaults, and updates the context.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_brief_data = {
        "theme_hint": "Minimalist Jackets",
        "garment_type": "Jacket",
        "brand_category": "Luxury",
        "target_audience": "Professionals",
        "region": "Europe",
        "key_attributes": ["Clean", "Structured"],
        "season": "auto",
        "year": "auto",
        "target_gender": "Female",
        "target_model_ethnicity": "European",
        "target_age_group": "Adult (30-50)",
        "desired_mood": ["Sophisticated", "Understated"],
    }
    mock_invoker.return_value = StructuredBriefModel.model_validate(mock_brief_data)
    processor = BriefDeconstructionProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    mock_invoker.assert_called_once()
    assert context.enriched_brief["theme_hint"] == "Minimalist Jackets"
    assert context.theme_slug == "minimalist-jack"  # Slug gets truncated
    # Test that operational defaults were applied
    assert context.enriched_brief["season"] in ["Spring/Summer", "Fall/Winter"]
    assert isinstance(context.enriched_brief["year"], str)


@pytest.mark.asyncio
async def test_brief_deconstruction_failure_path(mocker, run_context):
    """
    Tests that BriefDeconstructionProcessor raises a critical ValueError if the
    AI call fails permanently, as this is a pipeline-halting step.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.side_effect = MaxRetriesExceededError(
        last_exception=ValueError("AI failed")
    )
    processor = BriefDeconstructionProcessor()

    # ACT & ASSERT
    with pytest.raises(ValueError, match="Brief deconstruction failed permanently"):
        await processor.process(run_context)


@pytest.mark.asyncio
async def test_ethos_clarification_happy_path(mocker, run_context):
    """
    Tests that EthosClarificationProcessor correctly updates the context's brand_ethos.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.return_value = EthosModel(
        ethos="A focus on sustainable craftsmanship."
    )
    processor = EthosClarificationProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    assert context.brand_ethos == "A focus on sustainable craftsmanship."


@pytest.mark.asyncio
async def test_ethos_clarification_failure_path(mocker, run_context):
    """
    Tests that EthosClarificationProcessor provides a safe, empty default
    for brand_ethos if the AI call fails, allowing the pipeline to continue.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.side_effect = MaxRetriesExceededError(
        last_exception=ValueError("AI failed")
    )
    processor = EthosClarificationProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    assert context.brand_ethos == ""  # Should be an empty string, not None or crash


@pytest.mark.asyncio
async def test_brief_enrichment_happy_path(mocker, run_context):
    """
    Tests that BriefEnrichmentProcessor correctly calls all three AI functions
    concurrently and enriches the brief with all expected data.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    # Use side_effect to provide different return values for each call
    mock_invoker.side_effect = [
        ConceptsModel(concepts=["concept1", "concept2"]),
        AntagonistSynthesisModel(antagonist_synthesis="A surprising detail."),
        KeywordsModel(keywords=["keyword1", "keyword2"]),
    ]

    # Pre-populate the context as if the deconstruction step already ran
    run_context.enriched_brief = {"theme_hint": "Test Theme", "garment_type": "Coat"}
    processor = BriefEnrichmentProcessor()

    # ACT
    context = await processor.process(run_context)

    # ASSERT
    assert mock_invoker.call_count == 3
    assert context.enriched_brief["expanded_concepts"] == ["concept1", "concept2"]
    assert context.antagonist_synthesis == "A surprising detail."
    # The keywords list should contain the original theme and the new keywords
    assert "Test Theme" in context.enriched_brief["search_keywords"]
    assert "keyword1" in context.enriched_brief["search_keywords"]
    assert "keyword2" in context.enriched_brief["search_keywords"]
