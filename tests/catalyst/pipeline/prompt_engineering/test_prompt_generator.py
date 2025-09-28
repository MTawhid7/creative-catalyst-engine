# tests/catalyst/pipeline/prompt_engineering/test_prompt_generator.py

import pytest
from unittest.mock import MagicMock

from catalyst.models.trend_report import (
    FashionTrendReport,
    PromptMetadata,
    KeyPieceDetail,
    ReportNamedDescription,
)
from catalyst.pipeline.prompt_engineering.prompt_generator import (
    PromptGenerator,
    DEFAULT_STYLE_GUIDE,
)
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def strategic_fashion_report() -> FashionTrendReport:
    """A fixture designed to test strategic pairing and cycling."""
    return FashionTrendReport(
        prompt_metadata=PromptMetadata(run_id="strat-run", user_passage="test"),
        overarching_theme="Strategic Test Theme",
        desired_mood=["Strategic", "Varied", "Cohesive"],
        influential_models=[
            ReportNamedDescription(name="Muse One", description="..."),
            ReportNamedDescription(name="Muse Two", description="..."),
        ],
        cultural_drivers=[
            ReportNamedDescription(name="Driver One", description="..."),
            ReportNamedDescription(name="Driver Two", description="..."),
        ],
        detailed_key_pieces=[
            KeyPieceDetail(key_piece_name="Garment Alpha"),
            KeyPieceDetail(key_piece_name="Garment Beta"),
            KeyPieceDetail(key_piece_name="Garment Gamma"),
        ],
        season=["FW"],
        year=[2025],
        region=["Global"],
        target_gender="Any",
        target_age_group="Any",
        target_model_ethnicity="Any",
        antagonist_synthesis="test",
    )


@pytest.mark.asyncio
class TestStrategicPromptGenerator:
    """A rigorous test suite for the final, architecturally sound PromptGenerator."""

    async def test_strategic_pairing_and_cycling(
        self, strategic_fashion_report, mocker
    ):
        """
        The definitive test: verifies that garments are correctly and deterministically
        paired with muses and inspirations, including the cycling logic.
        """
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=DEFAULT_STYLE_GUIDE,
        )
        generator = PromptGenerator(
            report=strategic_fashion_report, research_dossier={}
        )
        prompts = await generator.generate_prompts()

        # --- START: THE DEFINITIVE FIX ---
        # The assertion strings must exactly match the template, including markdown.
        prompt_alpha = prompts["Garment Alpha"]["mood_board"]
        assert "embodying the **'Muse One'** persona" in prompt_alpha
        assert "core inspiration: **'Driver One'**" in prompt_alpha

        prompt_beta = prompts["Garment Beta"]["mood_board"]
        assert "embodying the **'Muse Two'** persona" in prompt_beta
        assert "core inspiration: **'Driver Two'**" in prompt_beta

        prompt_gamma = prompts["Garment Gamma"]["mood_board"]
        assert "embodying the **'Muse One'** persona" in prompt_gamma
        assert "core inspiration: **'Driver One'**" in prompt_gamma
        # --- END: THE DEFINITIVE FIX ---

    async def test_handles_empty_inspirational_lists(
        self, strategic_fashion_report, mocker
    ):
        """
        Verify that the generator provides safe, meaningful defaults if the
        influential_models or cultural_drivers lists are empty.
        """
        strategic_fashion_report.influential_models = []
        strategic_fashion_report.cultural_drivers = []

        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=DEFAULT_STYLE_GUIDE,
        )
        generator = PromptGenerator(
            report=strategic_fashion_report, research_dossier={}
        )
        prompts = await generator.generate_prompts()

        prompt_alpha = prompts["Garment Alpha"]["mood_board"]
        # --- START: THE DEFINITIVE FIX ---
        assert (
            "embodying the **'a mysterious, artistic figure'** persona" in prompt_alpha
        )
        assert "core inspiration: **'modern minimalist art'**" in prompt_alpha
        # --- END: THE DEFINITIVE FIX ---
