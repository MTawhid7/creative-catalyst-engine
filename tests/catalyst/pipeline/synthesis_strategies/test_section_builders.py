# tests/catalyst/pipeline/synthesis_strategies/test_section_builders.py

import pytest
from unittest.mock import MagicMock, AsyncMock

# Import the Pydantic models our builders now return
from catalyst.pipeline.synthesis_strategies.synthesis_models import (
    OverarchingThemeModel,
    CulturalDriversModel,
    InfluentialModelsModel,
    NarrativeSettingModel,
    AccessoriesModel,
    KeyPieceNamesModel,
)
from catalyst.models.trend_report import KeyPieceDetail

# Import the builders we are testing
from catalyst.pipeline.synthesis_strategies.section_builders import (
    TopLevelFieldsBuilder,
    NarrativeSettingBuilder,
    StrategiesBuilder,
    AccessoriesBuilder,
    KeyPiecesBuilder,
)

# Import the exception we will test for
from catalyst.resilience import MaxRetriesExceededError


# --- MOCK PATH ---
# This is the full path to the function we will be mocking in all tests.
INVOKER_PATH = (
    "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience"
)


@pytest.mark.asyncio
async def test_top_level_fields_builder_happy_path(mocker):
    """
    Tests that the TopLevelFieldsBuilder correctly assembles the dictionary
    from the Pydantic models returned by the invoker.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)

    # Configure the mock to return different Pydantic models on each call
    mock_invoker.side_effect = [
        OverarchingThemeModel(overarching_theme="Test Theme"),
        CulturalDriversModel(cultural_drivers=["driver1"]),
        InfluentialModelsModel(influential_models=["model1"]),
    ]

    builder = TopLevelFieldsBuilder(context=MagicMock())

    # ACT
    result = await builder.build(research_context="some research", is_fallback=False)

    # ASSERT
    assert result["overarching_theme"] == "Test Theme"
    assert result["cultural_drivers"] == ["driver1"]
    assert result["influential_models"] == ["model1"]
    assert mock_invoker.call_count == 3


@pytest.mark.asyncio
async def test_narrative_setting_builder_happy_path(mocker):
    """
    Tests the NarrativeSettingBuilder's happy path.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.return_value = NarrativeSettingModel(
        narrative_setting="A test setting."
    )

    builder = NarrativeSettingBuilder(context=MagicMock(), theme="test", drivers=[])

    # ACT
    result = await builder.build(research_context="", is_fallback=False)

    # ASSERT
    assert result["narrative_setting_description"] == "A test setting."


@pytest.mark.asyncio
async def test_narrative_setting_builder_failure_path(mocker):
    """
    Tests that the NarrativeSettingBuilder returns a safe default when the invoker fails.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    # Configure the mock to raise the specific error the builder expects
    mock_invoker.side_effect = MaxRetriesExceededError(last_exception=ValueError())

    builder = NarrativeSettingBuilder(context=MagicMock(), theme="test", drivers=[])

    # ACT
    result = await builder.build(research_context="", is_fallback=False)

    # ASSERT
    assert (
        result["narrative_setting_description"]
        == "A minimalist, contemporary architectural setting."
    )


@pytest.mark.asyncio
async def test_accessories_builder_happy_path(mocker):
    """
    Tests the AccessoriesBuilder's happy path.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.return_value = AccessoriesModel(
        Bags=["Test Bag"], Footwear=[], Jewelry=[], Other=[]
    )

    builder = AccessoriesBuilder(
        context=MagicMock(), theme="", mood=[], drivers=[], models=[], strategy=""
    )

    # ACT
    result = await builder.build(research_context="", is_fallback=False)

    # ASSERT
    assert result["accessories"]["Bags"] == ["Test Bag"]


@pytest.mark.asyncio
async def test_accessories_builder_failure_path(mocker):
    """
    Tests that the AccessoriesBuilder returns a safe default when the invoker fails.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.side_effect = MaxRetriesExceededError(last_exception=ValueError())

    builder = AccessoriesBuilder(
        context=MagicMock(), theme="", mood=[], drivers=[], models=[], strategy=""
    )

    # ACT
    result = await builder.build(research_context="", is_fallback=False)

    # ASSERT
    assert result["accessories"]["Bags"] == []
    assert result["accessories"]["Footwear"] == []


@pytest.mark.asyncio
async def test_key_pieces_builder_primary_path_skips_failed_item(mocker):
    """
    Tests that the KeyPiecesBuilder's primary path gracefully skips a single
    failed AI call and continues to process the others.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)

    valid_key_piece = KeyPieceDetail(
        key_piece_name="Succeeded Piece",
        description="A successfully processed piece.",
        inspired_by_designers=[],
        wearer_profile="",
        patterns=[],
        fabrics=[],
        colors=[],
        silhouettes=[],
        lining=None,
        details_trims=[],
        suggested_pairings=[],
    )

    mock_invoker.side_effect = [
        valid_key_piece,
        MaxRetriesExceededError(last_exception=ValueError()),
    ]

    # --- START: THE FIX ---
    # Create two mock match objects that behave like re.Match objects.
    # Each one needs a .group() method that returns a string.
    mock_match_1 = MagicMock()
    mock_match_1.group.return_value = "Text for piece 1"

    mock_match_2 = MagicMock()
    mock_match_2.group.return_value = "Text for piece 2"

    # Now, mock the finditer call to return our list of mock match objects.
    mocker.patch("re.compile").return_value.finditer.return_value = [
        mock_match_1,
        mock_match_2,
    ]
    # --- END: THE FIX ---

    builder = KeyPiecesBuilder(context=MagicMock())

    # ACT
    result = await builder.build(research_context="mock research", is_fallback=False)

    # ASSERT
    assert len(result["detailed_key_pieces"]) == 1
    assert result["detailed_key_pieces"][0]["key_piece_name"] == "Succeeded Piece"
    assert mock_invoker.call_count == 2


# 1. DEFINE THE CORRECTED TEST SCENARIOS
strategies_builder_test_cases = [
    (
        "happy_path_primary",  # Test ID
        # --- START: THE FIX ---
        # Use the new XML-style tags instead of the Markdown fence.
        'Some text before... <strategic_narratives_json>{"tonal_story": "A tale of two cities.", "accessory_strategy": "Less is more."}</strategic_narratives_json> Some text after...',
        # --- END: THE FIX ---
        False,  # is_fallback
        "A tale of two cities.",  # Expected color strategy
        "Less is more.",  # Expected accessory strategy
    ),
    (
        "partial_json_primary",  # Test ID
        # --- START: THE FIX ---
        '<strategic_narratives_json>{"tonal_story": "A tale of one city."}</strategic_narratives_json>',
        # --- END: THE FIX ---
        False,  # is_fallback
        "A tale of one city.",  # Expects to find the one that exists
        "Accessories play a supportive role to complete the look.",  # Expects default for the missing one
    ),
    (
        "no_json_primary",  # Test ID
        "This is just plain text with no XML tag.",  # Input context with no tag
        False,  # is_fallback
        "No specific color strategy was defined.",  # Expects default
        "Accessories play a supportive role to complete the look.",  # Expects default
    ),
    (
        "fallback_path",  # Test ID
        "This research context should be ignored.",  # Input context
        True,  # is_fallback is TRUE
        "No specific color strategy was defined.",  # Expects the hardcoded fallback default
        "Accessories play a supportive role to complete the look.",  # Expects the hardcoded fallback default
    ),
]


# 2. CREATE THE NEW PARAMETERIZED TEST FUNCTION
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "test_id, input_research_context, is_fallback, expected_color_strategy, expected_accessory_strategy",
    strategies_builder_test_cases,
)
async def test_strategies_builder(
    mocker,
    test_id,
    input_research_context,
    is_fallback,
    expected_color_strategy,
    expected_accessory_strategy,
):
    """
    Tests the StrategiesBuilder's ability to parse JSON and handle its fallback logic.
    """
    # 3. ARRANGE
    # NOTE: We DO NOT need to mock the Gemini client here!
    # This builder's job is to parse a string, not to call the AI.
    # This makes it a true, simple unit test.
    mock_context = MagicMock()
    builder = StrategiesBuilder(context=mock_context)

    # 4. ACT
    result = await builder.build(
        research_context=input_research_context, is_fallback=is_fallback
    )

    # 5. ASSERT
    assert result is not None
    assert result["color_palette_strategy"] == expected_color_strategy
    assert result["accessory_strategy"] == expected_accessory_strategy
