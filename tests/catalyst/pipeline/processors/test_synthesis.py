# tests/catalyst/pipeline/processors/test_synthesis.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, call
import copy

from catalyst.context import RunContext
from catalyst.pipeline.processors.synthesis import (
    WebResearchProcessor,
    ReportSynthesisProcessor,
    KeyGarmentsProcessor,
)
from catalyst.pipeline.synthesis_strategies.synthesis_models import ResearchDossierModel
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    return RunContext(user_passage="test", results_dir=tmp_path, variation_seed=0)


@pytest.mark.asyncio
class TestWebResearchProcessor:
    async def test_process_success(self, run_context: RunContext, mocker):
        mock_dossier = ResearchDossierModel(trend_narrative="A deep analysis.")
        mocker.patch(
            "catalyst.pipeline.processors.synthesis.invoke_with_resilience",
            return_value=mock_dossier,
        )
        processor = WebResearchProcessor()
        context = await processor.process(run_context)
        assert (
            context.structured_research_context["trend_narrative"] == "A deep analysis."
        )


@pytest.mark.asyncio
class TestReportSynthesisProcessor:
    @pytest.fixture
    def mock_builders(self, mocker) -> dict:
        builders = {
            "NarrativeSynthesisBuilder": MagicMock(
                build=AsyncMock(return_value={"narrative": "data"})
            ),
            "CreativeAnalysisBuilder": MagicMock(
                build=AsyncMock(return_value={"analysis": "data"})
            ),
            "AccessoriesBuilder": MagicMock(
                build=AsyncMock(return_value={"accessories": "data"})
            ),
        }
        for name, mock_instance in builders.items():
            mocker.patch(
                f"catalyst.pipeline.processors.synthesis.{name}",
                return_value=mock_instance,
            )
        return builders

    async def test_process_success(self, run_context: RunContext, mock_builders: dict):
        run_context.structured_research_context = {"key": "value"}
        processor = ReportSynthesisProcessor()
        context = await processor.process(run_context)
        for name, mock_instance in mock_builders.items():
            mock_instance.build.assert_awaited_once()


@pytest.mark.asyncio
class TestKeyGarmentsProcessor:

    @pytest.fixture
    def mock_garment_builder(self, mocker) -> AsyncMock:
        mock_builder_instance = MagicMock()

        # The first argument is now positional, so we name it `_` to signify it's handled by position.
        async def stateful_side_effect(_, **kwargs):
            # We can get the list from call_args if needed, but for this simple side effect, it's not.
            # Let's count calls instead to generate unique names.
            garment_num = mock_builder_instance.build.call_count
            return {"key_piece": {"name": f"Garment {garment_num}"}}

        mock_builder_instance.build = AsyncMock(side_effect=stateful_side_effect)
        mocker.patch(
            "catalyst.pipeline.processors.synthesis.SingleGarmentBuilder",
            return_value=mock_builder_instance,
        )
        return mock_builder_instance.build

    async def test_process_collection_strategy(
        self, run_context: RunContext, mock_garment_builder: AsyncMock
    ):
        """Verify the 'collection' strategy now uses seeds to create diverse items."""
        run_context.enriched_brief = {"generation_strategy": "collection"}
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()
        await processor.process(run_context)

        assert mock_garment_builder.call_count == 3
        # FIX: The test must now expect the list as a POSITIONAL argument.
        mock_garment_builder.assert_has_awaits(
            [
                call(
                    [],
                    variation_seed_override=0,
                    specific_garment_override=None,
                ),
                call(
                    [{"name": "Garment 1"}],
                    variation_seed_override=1,
                    specific_garment_override=None,
                ),
                call(
                    [
                        {"name": "Garment 1"},
                        {"name": "Garment 2"},
                    ],
                    variation_seed_override=2,
                    specific_garment_override=None,
                ),
            ]
        )

    async def test_process_variations_strategy(
        self, run_context: RunContext, mock_garment_builder: AsyncMock
    ):
        run_context.enriched_brief = {"generation_strategy": "variations"}
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()
        await processor.process(run_context)
        assert mock_garment_builder.call_count == 3
        # FIX: The test must now expect the list as a POSITIONAL argument.
        mock_garment_builder.assert_has_awaits(
            [
                call(
                    [],
                    variation_seed_override=0,
                    specific_garment_override=None,
                ),
                call(
                    [{"name": "Garment 1"}],
                    variation_seed_override=1,
                    specific_garment_override=None,
                ),
                call(
                    [{"name": "Garment 1"}, {"name": "Garment 2"}],
                    variation_seed_override=2,
                    specific_garment_override=None,
                ),
            ]
        )

    async def test_process_specified_items_strategy(
        self, run_context: RunContext, mock_garment_builder: AsyncMock
    ):
        run_context.enriched_brief = {
            "generation_strategy": "specified_items",
            "explicit_garments": ["Test Coat", "Test Trousers"],
        }
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()
        await processor.process(run_context)
        assert mock_garment_builder.call_count == 2
        # FIX: The test must now expect the list as a POSITIONAL argument.
        mock_garment_builder.assert_has_awaits(
            [
                call(
                    [],
                    variation_seed_override=None,
                    specific_garment_override="Test Coat",
                ),
                call(
                    [{"name": "Garment 1"}],
                    variation_seed_override=None,
                    specific_garment_override="Test Trousers",
                ),
            ]
        )
