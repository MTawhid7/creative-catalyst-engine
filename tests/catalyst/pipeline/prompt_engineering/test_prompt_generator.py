# tests/catalyst/pipeline/prompt_engineering/test_prompt_generator.py

import pytest
from unittest.mock import MagicMock

from catalyst.models.trend_report import (
    FashionTrendReport,
    PromptMetadata,
    KeyPieceDetail,
    ReportNamedDescription,
)
from catalyst.pipeline.prompt_engineering.prompt_generator import PromptGenerator
from catalyst.resilience import MaxRetriesExceededError
from catalyst.pipeline.synthesis_strategies.synthesis_models import ArtDirectionModel


@pytest.fixture
def strategic_fashion_report() -> FashionTrendReport:
    return FashionTrendReport(
        prompt_metadata=PromptMetadata(run_id="strat-run", user_passage="test"),
        overarching_theme="Strategic Test Theme",
        desired_mood=["Strategic"],
        influential_models=[ReportNamedDescription(name="Muse One", description="...")],
        cultural_drivers=[ReportNamedDescription(name="Driver One", description="...")],
        detailed_key_pieces=[KeyPieceDetail(key_piece_name="Garment Alpha")],
        season=["FW"],
        year=[2025],
        region=["Global"],
        target_gender="Any",
        target_age_group="Any",
        target_model_ethnicity="Any",
        antagonist_synthesis="test",
    )


@pytest.fixture
def mock_art_direction_model() -> ArtDirectionModel:
    return ArtDirectionModel(
        narrative_setting_description="A mock setting from the test.",
        photographic_style="Test Camera Style",
        lighting_style="Test Lighting Style",
        film_aesthetic="Test Film Aesthetic",
        negative_style_keywords="no, bad, things",
    )


@pytest.mark.asyncio
class TestStrategicPromptGenerator:
    """A rigorous test suite for the final, refactored PromptGenerator."""

    async def test_generate_prompts_happy_path(
        self, strategic_fashion_report, mock_art_direction_model, mocker
    ):
        """
        Verify that the fields from the generated ArtDirectionModel are
        correctly injected into the final garment prompt.
        """
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=mock_art_direction_model,
        )
        generator = PromptGenerator(
            report=strategic_fashion_report, research_dossier={}
        )
        prompts, art_direction = await generator.generate_prompts()

        assert art_direction == mock_art_direction_model

        final_prompt = prompts["Garment Alpha"]["final_garment"]
        # --- CHANGE: Assertions now match the exact Markdown format of the template ---
        assert "-   **Photography:** Test Camera Style" in final_prompt
        assert "-   **Lighting:** Test Lighting Style" in final_prompt
        assert "-   **Aesthetic:** Test Film Aesthetic" in final_prompt
        assert "-   **Setting:** A mock setting from the test." in final_prompt
        assert (
            "-   **Stylistic Negative Keywords:** Avoid no, bad, things" in final_prompt
        )

    async def test_fallback_on_art_direction_failure(
        self, strategic_fashion_report, mocker
    ):
        """
        Verify that if the AI call for art direction fails, the system uses
        a default (empty) model and still generates prompts.
        """
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        generator = PromptGenerator(
            report=strategic_fashion_report, research_dossier={}
        )
        prompts, art_direction = await generator.generate_prompts()

        assert art_direction == ArtDirectionModel()

        final_prompt = prompts["Garment Alpha"]["final_garment"]
        # --- CHANGE: Assertions now match the empty state within the Markdown format ---
        assert "-   **Photography:** " in final_prompt
        assert "-   **Lighting:** " in final_prompt
        assert "-   **Aesthetic:** " in final_prompt
