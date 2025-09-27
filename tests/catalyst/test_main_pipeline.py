# tests/catalyst/test_main_pipeline.py

import pytest
import json
from pathlib import Path
from unittest.mock import AsyncMock

from catalyst.main import run_pipeline
from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError

# Import all Pydantic models for mocking
from catalyst.pipeline.processors.briefing import *
from catalyst.pipeline.synthesis_strategies.synthesis_models import *
from catalyst.pipeline.prompt_engineering.prompt_generator import (
    CreativeStyleGuideModel,
)


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    return RunContext(user_passage="A test passage.", results_dir=tmp_path)


@pytest.mark.asyncio
class TestRunPipeline:

    @pytest.fixture
    def mock_ai_client(self, mocker):
        """
        A consistent fixture that mocks the AI client. It returns a tuple:
        (the mock object, the dictionary of valid responses).
        """
        mock_responses = {
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
            ),
            EthosModel: EthosModel(ethos="Test Ethos"),
            ConceptsModel: ConceptsModel(concepts=["c1"]),
            AntagonistSynthesisModel: AntagonistSynthesisModel(
                antagonist_synthesis="twist"
            ),
            KeywordsModel: KeywordsModel(keywords=["k1"]),
            ResearchDossierModel: ResearchDossierModel(
                trend_narrative="Dossier Narrative"
            ),
            NarrativeSynthesisModel: NarrativeSynthesisModel(
                overarching_theme="Final Theme"
            ),
            CulturalDriversModel: CulturalDriversModel(cultural_drivers=[]),
            InfluentialModelsModel: InfluentialModelsModel(influential_models=[]),
            CommercialStrategyModel: CommercialStrategyModel(
                commercial_strategy_summary="strat"
            ),
            AccessoriesModel: AccessoriesModel(accessories=[]),
            NarrativeSettingModel: NarrativeSettingModel(
                narrative_setting_description="setting"
            ),
            SingleGarmentModel: SingleGarmentModel(
                key_piece=KeyPieceDetail(key_piece_name="Garment")
            ),
            CreativeStyleGuideModel: CreativeStyleGuideModel(
                art_direction="dir", negative_style_keywords="neg"
            ),
        }

        async def side_effect(**kwargs):
            response_schema = kwargs.get("response_schema")
            model_instance = mock_responses.get(response_schema)
            if model_instance:
                return {"text": model_instance.model_dump_json()}
            raise TypeError(f"Mock called with unconfigured schema: {response_schema}")

        mock = mocker.patch(
            "catalyst.resilience.invoker.gemini.generate_content_async",
            side_effect=side_effect,
        )
        return mock, mock_responses

    async def test_pipeline_happy_path_cache_miss(
        self, run_context: RunContext, mock_ai_client, mocker
    ):
        mock_client, _ = mock_ai_client
        mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async", return_value=None
        )
        mocker.patch("catalyst.caching.cache_manager.add_to_report_cache_async")
        mock_image_generator = AsyncMock()
        mock_image_generator.process.side_effect = lambda context: context
        mocker.patch(
            "catalyst.pipeline.orchestrator.get_image_generator",
            return_value=mock_image_generator,
        )

        final_context = await run_pipeline(run_context)

        assert final_context.final_report is not None
        assert final_context.final_report["overarching_theme"] == "Final Theme"
        assert mock_client.call_count > 10

    async def test_pipeline_cache_hit(
        self, run_context: RunContext, mock_ai_client, mocker
    ):
        mock_client, _ = mock_ai_client
        cached_report = {"final_report": {"overarching_theme": "Cached Theme"}}
        mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async",
            return_value=json.dumps(cached_report),
        )

        await run_pipeline(run_context)

        assert mock_client.call_count == 5

    async def test_pipeline_graceful_failure_on_critical_step(
        self, run_context: RunContext, mock_ai_client, mocker
    ):
        """Verify that a critical AI failure halts the pipeline and propagates the correct exception."""
        # --- START: THE DEFINITIVE FIX ---
        # Unpack the fixture tuple inside the test.
        mock_client, mock_responses = mock_ai_client

        async def fail_on_research(**kwargs):
            response_schema = kwargs.get("response_schema")
            if response_schema == ResearchDossierModel:
                raise MaxRetriesExceededError(
                    ValueError("Simulated permanent AI failure")
                )

            model_instance = mock_responses.get(response_schema)
            return {"text": model_instance.model_dump_json()}

        mock_client.side_effect = fail_on_research
        # --- END: THE DEFINITIVE FIX ---

        mocker.patch(
            "catalyst.caching.cache_manager.check_report_cache_async", return_value=None
        )

        with pytest.raises(MaxRetriesExceededError):
            await run_pipeline(run_context)
