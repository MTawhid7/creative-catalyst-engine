# tests/catalyst/pipeline/processors/test_synthesis.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
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
    return RunContext(user_passage="test", results_dir=tmp_path)


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

    async def test_process_failure(self, run_context: RunContext, mocker):
        mocker.patch(
            "catalyst.pipeline.processors.synthesis.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        processor = WebResearchProcessor()
        with pytest.raises(MaxRetriesExceededError):
            await processor.process(run_context)
        assert run_context.structured_research_context == {}


@pytest.mark.asyncio
class TestKeyGarmentsProcessor:
    @pytest.fixture
    def mock_garment_builder(self, mocker) -> tuple[MagicMock, list]:
        mock_instance = MagicMock()
        captured_args_history = []

        async def stateful_build_side_effect(previously_designed):
            captured_args_history.append(copy.deepcopy(previously_designed))
            call_num = len(captured_args_history)
            return {"key_piece": {"name": f"Garment {call_num}"}}

        mock_instance.build = AsyncMock(side_effect=stateful_build_side_effect)
        mocker.patch(
            "catalyst.pipeline.processors.synthesis.SingleGarmentBuilder",
            return_value=mock_instance,
        )
        return mock_instance, captured_args_history

    async def test_process_success_and_sequential_logic(
        self, run_context: RunContext, mock_garment_builder
    ):
        mock_builder_instance, captured_args = mock_garment_builder
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()
        context = await processor.process(run_context)
        assert mock_builder_instance.build.call_count == 3
        assert len(captured_args) == 3
        assert captured_args[0] == []
        assert len(captured_args[1]) == 1 and captured_args[1][0]["name"] == "Garment 1"
        assert len(captured_args[2]) == 2 and captured_args[2][1]["name"] == "Garment 2"

    async def test_process_handles_partial_failure(
        self, run_context: RunContext, mock_garment_builder
    ):
        mock_builder_instance, _ = mock_garment_builder
        mock_builder_instance.build.side_effect = [
            {"key_piece": {"name": "Garment 1"}},
            None,
            {"key_piece": {"name": "Garment 3"}},
        ]
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()
        context = await processor.process(run_context)
        assert mock_builder_instance.build.call_count == 3
        assert len(context.final_report["detailed_key_pieces"]) == 2


@pytest.mark.asyncio
class TestReportSynthesisProcessor:
    """Tests for the refactored, more efficient ReportSynthesisProcessor."""

    @pytest.fixture
    def mock_builders(self, mocker) -> dict:
        """Mocks the new, consolidated set of builder classes."""
        # --- CHANGE: Removed NarrativeSettingBuilder from the mock ---
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

    async def test_process_success(self, run_context: RunContext, mock_builders):
        """Verify all 3 builders are called and their results are assembled."""
        run_context.structured_research_context = {"key": "value"}
        processor = ReportSynthesisProcessor()
        context = await processor.process(run_context)

        # Assert that all 3 remaining builders were called
        for name, mock_instance in mock_builders.items():
            mock_instance.build.assert_awaited_once()

        assert context.final_report["narrative"] == "data"
        assert context.final_report["analysis"] == "data"
        assert context.final_report["accessories"] == "data"
        # --- CHANGE: Removed assertion for the non-existent "setting" data ---
        assert "setting" not in context.final_report

    async def test_process_skips_if_dossier_is_empty(
        self, run_context: RunContext, mock_builders
    ):
        """Verify that no builders are called if the research context is empty."""
        run_context.structured_research_context = {}
        processor = ReportSynthesisProcessor()
        context = await processor.process(run_context)
        for name, mock_instance in mock_builders.items():
            mock_instance.build.assert_not_called()
