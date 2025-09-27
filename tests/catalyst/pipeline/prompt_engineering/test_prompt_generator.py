# tests/catalyst/pipeline/prompt_engineering/test_prompt_generator.py

import pytest
from unittest.mock import MagicMock  # <-- FIX 1: Import MagicMock
from catalyst.models.trend_report import (
    FashionTrendReport,
    PromptMetadata,
    KeyPieceDetail,
    ColorDetail,
    FabricDetail,
    PatternDetail,
    ReportNamedDescription,
)
from catalyst.pipeline.prompt_engineering.prompt_generator import (
    PromptGenerator,
    CreativeStyleGuideModel,
    DEFAULT_STYLE_GUIDE,
)
from catalyst.resilience import MaxRetriesExceededError

# --- Fixtures ---

@pytest.fixture
def minimal_dossier() -> dict:
    """Provides a basic, non-empty research dossier."""
    return {"trend_narrative": "A minimal trend narrative."}


@pytest.fixture
def full_fashion_report() -> FashionTrendReport:
    """Provides a rich, validated FashionTrendReport object for testing."""
    return FashionTrendReport(
        prompt_metadata=PromptMetadata(run_id="test-run", user_passage="test-passage"),
        overarching_theme="Cyber-Baroque",
        trend_narrative_synthesis="A fusion of digital and classical.",
        cultural_drivers=[ReportNamedDescription(name="Digital Renaissance", description="...")],
        influential_models=[ReportNamedDescription(name="The Glitch Artist", description="...")],
        accessories=[ReportNamedDescription(name="Holographic Fan", description="...")],
        commercial_strategy_summary="Focus on limited digital drops.",
        narrative_setting_description="A neon-lit Venetian palazzo.",
        detailed_key_pieces=[
            KeyPieceDetail(
                key_piece_name="The Datamosh Corset",
                description="A digitally printed corset.",
                colors=[ColorDetail(name="Glitch Green"), ColorDetail(name="Royal Purple")],
                fabrics=[FabricDetail(material="Neoprene", texture="Smooth")],
                patterns=[PatternDetail(motif="Pixelated Damask")],
                details_trims=["Fiber-optic piping"],
                lining="Breathable mesh.",
                suggested_pairings=["Asymmetrical Tulle Skirt"],
            ),
            KeyPieceDetail(key_piece_name="The Empty Gown"), # For testing missing data
        ],
        season=["Fall/Winter"],
        year=[2025],
        region=["Global"],
        target_gender="Female",
        target_age_group="Young Adult (20-30)",
        target_model_ethnicity="Any",
        antagonist_synthesis="A creative twist."
    )


# --- Unit Tests for Helper Methods ---

class TestPromptGeneratorHelpers:
    """Unit tests for the private helper methods of the PromptGenerator."""

    def test_get_visual_color_palette(self):
        """Test color palette sentence construction."""
        piece_full = KeyPieceDetail(colors=[ColorDetail(name="Red"), ColorDetail(name="Blue")])
        piece_single = KeyPieceDetail(colors=[ColorDetail(name="Green")])
        piece_empty = KeyPieceDetail(colors=[])

        generator_full = PromptGenerator(report=MagicMock(), research_dossier={})

        assert generator_full._get_visual_color_palette(piece_full) == "A refined color palette of Red and Blue."
        assert generator_full._get_visual_color_palette(piece_single) == "The piece is rendered in a striking shade of Green."
        assert "thematically appropriate" in generator_full._get_visual_color_palette(piece_empty)

    def test_get_visual_fabric_description(self):
        """Test fabric description sentence construction."""
        piece_full = KeyPieceDetail(fabrics=[FabricDetail(material="Silk", texture="Velvety")])
        piece_empty = KeyPieceDetail(fabrics=[])

        generator = PromptGenerator(report=MagicMock(), research_dossier={})

        assert "Crafted from a luxurious Velvety Silk" in generator._get_visual_fabric_description(piece_full)
        assert "high-quality, modern textile" in generator._get_visual_fabric_description(piece_empty)

    def test_get_visual_details_description(self):
        """Test details description sentence construction, including lining."""
        piece_full = KeyPieceDetail(details_trims=["Gold Buttons", "Embroidery"], lining="Satin")
        piece_empty = KeyPieceDetail()

        generator = PromptGenerator(report=MagicMock(), research_dossier={})

        desc = generator._get_visual_details_description(piece_full)
        assert "Key construction details include Gold Buttons, Embroidery." in desc
        assert "It is lined with Satin for a luxurious finish." in desc
        assert "minimalist detailing" in generator._get_visual_details_description(piece_empty)


# --- Integration Tests for Main Methods ---

@pytest.mark.asyncio
class TestPromptGeneratorMain:
    """Integration tests for the main methods of the PromptGenerator."""

    async def test_generate_creative_style_guide_success(self, full_fashion_report, minimal_dossier, mocker):
        """Test style guide generation on a successful AI call."""
        # Arrange
        mock_response = CreativeStyleGuideModel(
            art_direction="Test Direction",
            negative_style_keywords="Test Negatives",
        )
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=mock_response,
        )
        generator = PromptGenerator(report=full_fashion_report, research_dossier=minimal_dossier)

        # Act
        style_guide = await generator._generate_creative_style_guide()

        # Assert
        assert style_guide.art_direction == "Test Direction"

    async def test_generate_creative_style_guide_failure(self, full_fashion_report, minimal_dossier, mocker):
        """Test that style guide generation falls back to the default on AI failure."""
        # Arrange
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        generator = PromptGenerator(report=full_fashion_report, research_dossier=minimal_dossier)

        # Act
        style_guide = await generator._generate_creative_style_guide()

        # Assert
        assert style_guide == DEFAULT_STYLE_GUIDE

    async def test_generate_prompts_full_report(self, full_fashion_report, minimal_dossier, mocker):
        """Test the main prompt generation method with a full report."""
        # Arrange
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=DEFAULT_STYLE_GUIDE,
        )
        generator = PromptGenerator(report=full_fashion_report, research_dossier=minimal_dossier)

        # Act
        prompts = await generator.generate_prompts()

        # Assert
        assert "The Datamosh Corset" in prompts
        assert "The Empty Gown" in prompts

        corset_prompts = prompts["The Datamosh Corset"]
        assert "mood_board" in corset_prompts
        assert "final_garment" in corset_prompts

        # Check for key details in the final prompt
        assert "Datamosh Corset" in corset_prompts["final_garment"]
        assert "Glitch Green and Royal Purple" in corset_prompts["final_garment"]
        assert "A neon-lit Venetian palazzo" in corset_prompts["final_garment"]

    async def test_generate_prompts_empty_report(self, minimal_dossier, mocker):
        """Test that prompt generation handles a report with no key pieces."""
        # Arrange
        # --- FIX 2: Provide all required fields for the model ---
        empty_report = FashionTrendReport(
            prompt_metadata=PromptMetadata(run_id="test", user_passage="test"),
            season=["Spring"],
            year=[2025],
            region=["N/A"],
            target_gender="Any",
            target_age_group="N/A",
            target_model_ethnicity="Any",
            antagonist_synthesis="N/A",
        )
        mocker.patch(
            "catalyst.pipeline.prompt_engineering.prompt_generator.invoke_with_resilience",
            return_value=DEFAULT_STYLE_GUIDE,
        )
        generator = PromptGenerator(report=empty_report, research_dossier=minimal_dossier)

        # Act
        prompts = await generator.generate_prompts()

        # Assert
        assert prompts == {}