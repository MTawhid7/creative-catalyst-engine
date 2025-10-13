# tests/catalyst/pipeline/synthesis_strategies/test_section_builders.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from catalyst.context import RunContext
from catalyst.resilience import MaxRetriesExceededError
from catalyst.pipeline.synthesis_strategies.section_builders import (
    NarrativeSynthesisBuilder,
    CreativeAnalysisBuilder,
    AccessoriesBuilder,
    SingleGarmentBuilder,
)
from catalyst.pipeline.synthesis_strategies.synthesis_models import *
from catalyst.models.trend_report import KeyPieceDetail


@pytest.fixture
def run_context(tmp_path: Path, variation_seed: int = 0) -> RunContext:
    # Allow parameterizing the context's seed for different test scenarios
    context = RunContext(
        user_passage="test", results_dir=tmp_path, variation_seed=variation_seed
    )
    context.enriched_brief = {"theme_hint": "Test Theme"}
    return context


@pytest.fixture
def research_dossier() -> dict:
    return {"trend_narrative": "A test narrative."}


# ... (TestConsolidatedBuilders and parts of TestUniqueBuilders remain unchanged) ...
@pytest.mark.asyncio
class TestConsolidatedBuilders:
    async def test_creative_analysis_builder_success(
        self, run_context, research_dossier, mocker
    ):
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
        assert (
            result is not None and result["commercial_strategy_summary"] == "Sell more."
        )


@pytest.mark.asyncio
class TestUniqueBuilders:
    # --- START: REWRITTEN TESTS for SingleGarmentBuilder ---
    @pytest.fixture
    def mock_invoke(self, mocker) -> AsyncMock:
        """Mocks the invoke_with_resilience function."""
        mock_key_piece = KeyPieceDetail(key_piece_name="Test Garment")
        mock_response = SingleGarmentModel(key_piece=mock_key_piece)
        return mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.invoke_with_resilience",
            return_value=mock_response,
        )

    @pytest.fixture
    def mock_prompt_lib(self, mocker) -> MagicMock:
        """Mocks the prompt_library to check which prompt was used."""
        return mocker.patch(
            "catalyst.pipeline.synthesis_strategies.section_builders.prompt_library"
        )

    async def test_builder_uses_standard_prompt_for_seed_0(
        self, run_context, research_dossier, mock_invoke, mock_prompt_lib
    ):
        """Verify that seed 0 or no override uses the standard prompt."""
        builder = SingleGarmentBuilder(run_context, research_dossier)
        await builder.build(previously_designed_garments=[])

        # Verify the correct prompt was selected
        assert mock_invoke.call_args[0][1].startswith(
            mock_prompt_lib.SINGLE_GARMENT_SYNTHESIS_PROMPT
        )

    @pytest.mark.parametrize("run_context", [1, 5], indirect=True)
    async def test_builder_uses_variant_prompt_for_seed_gt_0(
        self, run_context, research_dossier, mock_invoke, mock_prompt_lib
    ):
        """Verify that a seed > 0 uses the variant prompt."""
        builder = SingleGarmentBuilder(run_context, research_dossier)
        await builder.build(previously_designed_garments=[])

        # Verify the correct prompt was selected
        assert mock_invoke.call_args[0][1].startswith(
            mock_prompt_lib.VARIANT_GARMENT_SYNTHESIS_PROMPT
        )

    async def test_builder_uses_variation_seed_override(
        self, run_context, research_dossier, mock_invoke, mock_prompt_lib
    ):
        """Verify that the override takes precedence over the context's seed."""
        builder = SingleGarmentBuilder(
            run_context, research_dossier
        )  # context has seed=0
        await builder.build(previously_designed_garments=[], variation_seed_override=2)

        # Verify the variant prompt was used due to the override
        assert mock_invoke.call_args[0][1].startswith(
            mock_prompt_lib.VARIANT_GARMENT_SYNTHESIS_PROMPT
        )

    async def test_builder_passes_specific_garment_override(
        self, run_context, research_dossier, mock_invoke
    ):
        """Verify the garment override is correctly formatted into the prompt."""
        builder = SingleGarmentBuilder(run_context, research_dossier)
        await builder.build(
            previously_designed_garments=[], specific_garment_override="Test Jumpsuit"
        )

        final_prompt = mock_invoke.call_args[0][1]
        # FIX: Include Markdown formatting present in prompt_library.py
        assert "**Garment to Design:** Test Jumpsuit" in final_prompt

    # --- END: REWRITTEN TESTS ---
