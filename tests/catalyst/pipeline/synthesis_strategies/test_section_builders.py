# tests/catalyst/pipeline/synthesis_strategies/test_section_builders.py

import pytest
from pathlib import Path

from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError
from catalyst.pipeline.synthesis_strategies.section_builders import (
    NarrativeSynthesisBuilder,
    CreativeAnalysisBuilder,  # New
    AccessoriesBuilder,
    NarrativeSettingBuilder,
    SingleGarmentBuilder,
)
from catalyst.pipeline.synthesis_strategies.synthesis_models import (
    NarrativeSynthesisModel,
    CreativeAnalysisModel,  # New
    AccessoriesModel,
    NarrativeSettingModel,
    SingleGarmentModel,
    NamedDescriptionModel,
)
from catalyst.models.trend_report import KeyPieceDetail


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.enriched_brief = {"theme_hint": "Test Theme"}
    return context


@pytest.fixture
def research_dossier() -> dict:
    return {"trend_narrative": "A test narrative."}


@pytest.mark.asyncio
class TestConsolidatedBuilders:
    """Tests for the new, consolidated builder architecture."""

    async def test_creative_analysis_builder_success(
        self, run_context, research_dossier, mocker
    ):
        """Verify the new consolidated builder returns the correct multi-part dictionary."""
        mock_response = CreativeAnalysisModel(
            cultural_drivers=[NamedDescriptionModel(name="Driver", description="Desc")],
            influential_models=[
                NamedDescriptionModel(name="Model", description="Desc")
            ],
            commercial_strategy_summary="Sell more.",
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )

        builder = CreativeAnalysisBuilder(run_context, research_dossier)
        result = await builder.build()

        assert result is not None
        assert len(result["cultural_drivers"]) == 1
        assert result["influential_models"][0]["name"] == "Model"
        assert result["commercial_strategy_summary"] == "Sell more."

    async def test_creative_analysis_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        """Verify the consolidated builder returns a safe, structured default on failure."""
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )

        builder = CreativeAnalysisBuilder(run_context, research_dossier)
        result = await builder.build()

        assert result is not None
        assert result["cultural_drivers"] == []
        assert result["influential_models"] == []
        assert result["commercial_strategy_summary"] == ""


# The old tests for CulturalDriversBuilder, etc., are now deleted.
# The tests for the remaining unique builders are still valid.


@pytest.mark.asyncio
class TestUniqueBuilders:
    async def test_narrative_synthesis_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = NarrativeSynthesisBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is None

    async def test_single_garment_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_key_piece = KeyPieceDetail(key_piece_name="Test Garment")
        mock_response = SingleGarmentModel(key_piece=mock_key_piece)
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = SingleGarmentBuilder(run_context, research_dossier)
        result = await builder.build(previously_designed_garments=[])
        assert result is not None
        assert result["key_piece"]["key_piece_name"] == "Test Garment"
