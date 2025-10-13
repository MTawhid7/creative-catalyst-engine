# tests/catalyst/test_main_pipeline.py

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock

from catalyst.main import run_pipeline
from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError

from catalyst.pipeline.processors.briefing import *
from catalyst.pipeline.synthesis_strategies.synthesis_models import *
from catalyst.models.trend_report import KeyPieceDetail


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    # This fixture provides the default seed=0 context
    return RunContext(
        user_passage="A test passage.", results_dir=tmp_path, variation_seed=0
    )


@pytest.fixture
def mock_responses() -> dict:
    """A single, comprehensive fixture for all mock Pydantic model responses."""
    return {
        StructuredBriefModel: StructuredBriefModel(
            theme_hint="Test-Theme",
            garment_type="Jacket",
            brand_category="Luxe",
            target_audience="All",
            region="Global",
            key_attributes=["A"],
            season="FW",
            year=2025,
            target_gender="Any",
            target_model_ethnicity="Any",
            target_age_group="All",
            desired_mood=["B"],
            generation_strategy="collection",
            explicit_garments=None,
        ),
        ConsolidatedBriefingModel: ConsolidatedBriefingModel(
            ethos="Test Ethos", expanded_concepts=["c1"], search_keywords=["k1"]
        ),
        AntagonistSynthesisModel: AntagonistSynthesisModel(
            antagonist_synthesis="twist"
        ),
        ResearchDossierModel: ResearchDossierModel(trend_narrative="Dossier Narrative"),
        NarrativeSynthesisModel: NarrativeSynthesisModel(
            overarching_theme="Final Theme"
        ),
        CreativeAnalysisModel: CreativeAnalysisModel(
            cultural_drivers=[],
            influential_models=[],
            commercial_strategy_summary="strat",
        ),
        AccessoriesModel: AccessoriesModel(accessories=[]),
        SingleGarmentModel: SingleGarmentModel(
            key_piece=KeyPieceDetail(key_piece_name="Garment")
        ),
        ArtDirectionModel: ArtDirectionModel(
            narrative_setting_description="A test setting."
        ),
    }


@pytest.fixture
def mock_ai_client(mocker, mock_responses: dict) -> AsyncMock:
    """A robust mock fixture that returns the correct mock response based on the schema."""

    async def side_effect(**kwargs):
        response_schema = kwargs.get("response_schema")
        model_instance = mock_responses.get(response_schema)
        if model_instance:
            return {"text": model_instance.model_dump_json()}
        raise TypeError(f"Mock called with unconfigured schema: {response_schema}")

    return mocker.patch(
        "catalyst.resilience.invoker.gemini.generate_content_async",
        side_effect=side_effect,
    )


@pytest.mark.asyncio
class TestRunPipeline:
    """Comprehensive integration tests for the main run_pipeline function."""

    async def test_pipeline_happy_path_cache_miss(
        self, run_context: RunContext, mock_ai_client, mocker
    ):
        """Verify the full pipeline runs successfully with seed 0 and a cache miss."""
        mock_check_cache = mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async", return_value=None
        )
        mocker.patch("catalyst.caching.cache_manager.add_to_report_cache_async")
        mock_image_generator = AsyncMock(
            process=AsyncMock(side_effect=lambda context: context)
        )
        mocker.patch(
            "catalyst.pipeline.orchestrator.get_image_generator",
            return_value=mock_image_generator,
        )

        final_context = await run_pipeline(run_context)

        mock_check_cache.assert_awaited_once()  # Should be called for seed 0
        assert final_context.final_report is not None
        assert final_context.final_report["overarching_theme"] == "Final Theme"
        assert mock_ai_client.call_count == 11

    # --- START: NEW TEST CASE ---
    async def test_pipeline_bypasses_l1_cache_for_non_zero_seed(
        self, tmp_path: Path, mock_ai_client, mocker
    ):
        """
        Verify that the L1 cache check is SKIPPED when the variation seed is > 0,
        forcing a full pipeline run to generate a new variation.
        """
        # Arrange: Create a context with a non-zero seed
        variation_context = RunContext(
            user_passage="A test passage.", results_dir=tmp_path, variation_seed=1
        )
        # Mock the cache check function. It should not be called.
        mock_check_cache = mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async",
            return_value=json.dumps(
                {"final_report": {"overarching_theme": "Should Be Ignored"}}
            ),
        )
        mocker.patch("catalyst.caching.cache_manager.add_to_report_cache_async")
        mocker.patch(
            "catalyst.pipeline.orchestrator.get_image_generator",
            return_value=AsyncMock(process=AsyncMock(side_effect=lambda ctx: ctx)),
        )

        # Act
        final_context = await run_pipeline(variation_context)

        # Assert
        mock_check_cache.assert_not_called()  # Crucial: verify the cache was bypassed
        assert final_context.final_report is not None
        # Verify it ran the full pipeline by checking for the theme from the mock AI, not the ignored cache
        assert final_context.final_report["overarching_theme"] == "Final Theme"
        assert mock_ai_client.call_count == 11

    # --- END: NEW TEST CASE ---

    async def test_pipeline_cache_hit(
        self, run_context: RunContext, mock_ai_client, mocker
    ):
        """Verify the pipeline exits early with seed 0 and a cache hit."""
        cached_report = {"final_report": {"overarching_theme": "Cached Theme"}}
        mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async",
            return_value=json.dumps(cached_report),
        )
        await run_pipeline(run_context)
        # Only briefing AI calls should happen before cache check
        assert mock_ai_client.call_count == 3

    async def test_pipeline_graceful_failure_on_critical_step(
        self, run_context: RunContext, mock_ai_client, mock_responses, mocker
    ):
        """Verify a critical failure after a cache miss raises an error."""

        async def fail_on_research(**kwargs):
            response_schema = kwargs.get("response_schema")
            if response_schema == ResearchDossierModel:
                raise MaxRetriesExceededError(ValueError("Simulated AI failure"))
            return {"text": mock_responses[response_schema].model_dump_json()}

        mock_ai_client.side_effect = fail_on_research
        mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async", return_value=None
        )
        with pytest.raises(MaxRetriesExceededError):
            await run_pipeline(run_context)
