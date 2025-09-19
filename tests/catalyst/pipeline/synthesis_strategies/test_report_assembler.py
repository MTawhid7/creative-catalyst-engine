# tests/catalyst/pipeline/synthesis_strategies/test_report_assembler.py

import pytest
from unittest.mock import patch, AsyncMock

from catalyst.context import RunContext
from catalyst.pipeline.synthesis_strategies.report_assembler import ReportAssembler

# Define paths to all the builder classes we need to mock
BUILDER_BASE_PATH = "catalyst.pipeline.synthesis_strategies.report_assembler"
TOP_LEVEL_BUILDER_PATH = f"{BUILDER_BASE_PATH}.TopLevelFieldsBuilder"
NARRATIVE_BUILDER_PATH = f"{BUILDER_BASE_PATH}.NarrativeSettingBuilder"
STRATEGIES_BUILDER_PATH = f"{BUILDER_BASE_PATH}.StrategiesBuilder"
ACCESSORIES_BUILDER_PATH = f"{BUILDER_BASE_PATH}.AccessoriesBuilder"
KEY_PIECES_BUILDER_PATH = f"{BUILDER_BASE_PATH}.KeyPiecesBuilder"


@pytest.fixture
def mock_builders(mocker):
    """Mocks all section builder classes and configures their build methods."""
    builders = {
        "top_level": mocker.patch(TOP_LEVEL_BUILDER_PATH).return_value,
        "narrative": mocker.patch(NARRATIVE_BUILDER_PATH).return_value,
        "strategies": mocker.patch(STRATEGIES_BUILDER_PATH).return_value,
        "accessories": mocker.patch(ACCESSORIES_BUILDER_PATH).return_value,
        "key_pieces": mocker.patch(KEY_PIECES_BUILDER_PATH).return_value,
    }

    # Configure the return values for the .build() method of each mock
    builders["top_level"].build = AsyncMock(
        return_value={"overarching_theme": "mock theme"}
    )
    builders["narrative"].build = AsyncMock(
        return_value={"narrative_setting_description": "mock setting"}
    )
    builders["strategies"].build = AsyncMock(
        return_value={"color_palette_strategy": "mock color strategy"}
    )
    builders["accessories"].build = AsyncMock(
        return_value={"accessories": {"Bags": ["mock bag"]}}
    )

    # --- START: THE FIX ---
    # Provide a valid KeyPieceDetail object that includes all required fields.
    builders["key_pieces"].build = AsyncMock(
        return_value={
            "detailed_key_pieces": [
                {
                    "key_piece_name": "mock piece",
                    "description": "A mock description.",
                    # Other fields have defaults, so we only need to provide the required ones.
                }
            ]
        }
    )
    # --- END: THE FIX ---

    return builders


@pytest.fixture
def run_context(tmp_path):
    """Provides a fresh RunContext for each test."""
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.enriched_brief = {
        "desired_mood": [],
        "season": "test",
        "year": "2025",
        "region": "test",
        "target_gender": "test",
        "target_age_group": "test",
        "target_model_ethnicity": "test",
    }
    context.structured_research_context = "some research context"
    return context


@pytest.mark.asyncio
async def test_report_assembler_happy_path(mock_builders, run_context):
    """
    Tests that the assembler correctly calls all builders, merges their results,
    and returns a valid, finalized report dictionary.
    """
    # ARRANGE
    assembler = ReportAssembler(context=run_context)

    # ACT
    final_report = await assembler.assemble_report()

    # ASSERT
    # 1. Verify all builders' .build() methods were called once.
    for name, builder in mock_builders.items():
        builder.build.assert_called_once()

    # 2. Verify the final report contains a merged set of keys from the mock builders.
    assert final_report is not None
    assert final_report["overarching_theme"] == "mock theme"
    assert final_report["narrative_setting_description"] == "mock setting"
    assert final_report["accessories"]["Bags"][0] == "mock bag"
    assert final_report["detailed_key_pieces"][0]["key_piece_name"] == "mock piece"

    # 3. Verify the assembler added its own metadata.
    assert "prompt_metadata" in final_report
    assert final_report["prompt_metadata"]["run_id"] == run_context.run_id


@pytest.mark.asyncio
async def test_report_assembler_returns_none_on_validation_error(
    mock_builders, run_context
):
    """
    Tests that if the merged data fails the final Pydantic validation,
    the assembler gracefully returns None.
    """
    # ARRANGE
    # Configure one of the builders to return incomplete data (missing a required field
    # like 'overarching_theme'), which will cause the FashionTrendReport validation to fail.
    mock_builders["top_level"].build.return_value = {"this_is_not_a_valid_key": "test"}

    assembler = ReportAssembler(context=run_context)

    # ACT
    final_report = await assembler.assemble_report()

    # ASSERT
    assert final_report is None
