# tests/catalyst/pipeline/synthesis_strategies/test_section_builders.py

import pytest
from pathlib import Path

from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError
from catalyst.pipeline.synthesis_strategies.section_builders import (
    NarrativeSynthesisBuilder,
    CulturalDriversBuilder,
    InfluentialModelsBuilder,
    CommercialStrategyBuilder,
    AccessoriesBuilder,
    NarrativeSettingBuilder,
    SingleGarmentBuilder,
)
from catalyst.pipeline.synthesis_strategies.synthesis_models import (
    NarrativeSynthesisModel,
    CulturalDriversModel,
    InfluentialModelsModel,
    CommercialStrategyModel,
    AccessoriesModel,
    NarrativeSettingModel,
    SingleGarmentModel,
    NamedDescriptionModel,
)
from catalyst.models.trend_report import KeyPieceDetail


# --- Fixtures ---


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.enriched_brief = {"theme_hint": "Test Theme"}
    context.brand_ethos = "Test Ethos"
    return context


@pytest.fixture
def research_dossier() -> dict:
    return {"trend_narrative": "A test narrative from the dossier."}


# --- Tests for Each Builder ---


@pytest.mark.asyncio
class TestAllBuilders:
    """A single class to hold tests for all builder strategies."""

    async def test_narrative_synthesis_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_response = NarrativeSynthesisModel(
            overarching_theme="Test Theme", trend_narrative_synthesis="Test Narrative"
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = NarrativeSynthesisBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert result["overarching_theme"] == "Test Theme"

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

    # --- START: DEFINITIVE FIX ---

    async def test_cultural_drivers_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_response = CulturalDriversModel(
            cultural_drivers=[NamedDescriptionModel(name="Driver", description="Desc")]
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = CulturalDriversBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert len(result["cultural_drivers"]) == 1
        assert result["cultural_drivers"][0]["name"] == "Driver"  # Use dict access

    async def test_cultural_drivers_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = CulturalDriversBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert result["cultural_drivers"] == []

    async def test_influential_models_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_response = InfluentialModelsModel(
            influential_models=[NamedDescriptionModel(name="Model", description="Desc")]
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = InfluentialModelsBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert len(result["influential_models"]) == 1
        assert result["influential_models"][0]["name"] == "Model"  # Use dict access

    async def test_influential_models_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = InfluentialModelsBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert result["influential_models"] == []

    async def test_commercial_strategy_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_response = CommercialStrategyModel(
            commercial_strategy_summary="Sell more."
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = CommercialStrategyBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert result["commercial_strategy_summary"] == "Sell more."

    async def test_commercial_strategy_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = CommercialStrategyBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is None

    async def test_accessories_builder_success(
        self, run_context, research_dossier, mocker
    ):
        mock_response = AccessoriesModel(
            accessories=[NamedDescriptionModel(name="Accessory", description="Desc")]
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )
        builder = AccessoriesBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert len(result["accessories"]) == 1
        assert result["accessories"][0]["name"] == "Accessory"  # Use dict access

    async def test_accessories_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = AccessoriesBuilder(run_context, research_dossier)
        result = await builder.build()
        assert result is not None
        assert result["accessories"] == {}  # Correct fallback value

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
        assert (
            result["key_piece"]["key_piece_name"] == "Test Garment"
        )  # Use dict access

    async def test_single_garment_builder_failure(
        self, run_context, research_dossier, mocker
    ):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        builder = SingleGarmentBuilder(run_context, research_dossier)
        result = await builder.build(previously_designed_garments=[])
        assert result is None

    # --- END: DEFINITIVE FIX ---
