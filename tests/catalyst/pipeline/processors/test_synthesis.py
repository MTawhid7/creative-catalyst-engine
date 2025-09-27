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
    """Provides a fresh RunContext for each test."""
    return RunContext(user_passage="test", results_dir=tmp_path)


@pytest.mark.asyncio
class TestWebResearchProcessor:
    async def test_process_success(self, run_context: RunContext, mocker):
        """Verify a successful AI call populates the research context."""
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
        """Verify that a critical AI failure is re-raised and the context is left clean."""
        # Arrange
        mocker.patch(
            "catalyst.pipeline.processors.synthesis.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        processor = WebResearchProcessor()

        # Act & Assert for the exception
        with pytest.raises(MaxRetriesExceededError):
            await processor.process(run_context)

        # --- START: THE DEFINITIVE FIX ---
        # Assert the final state of the context *after* the exception has been caught.
        assert run_context.structured_research_context == {}
        # --- END: THE DEFINITIVE FIX ---


@pytest.mark.asyncio
class TestKeyGarmentsProcessor:

    # --- START: THE DEFINITIVE, ROBUST MOCK FIX ---
    @pytest.fixture
    def mock_garment_builder(self, mocker) -> tuple[MagicMock, list]:
        """
        Mocks the SingleGarmentBuilder with a stateful async function as a side_effect.
        This is the most robust way to test sequential logic with mutable arguments.
        It returns the mock and a list to record the state of arguments at each call.
        """
        mock_instance = MagicMock()

        # This list will store a snapshot of the arguments at each call.
        captured_args_history = []

        # The stateful side_effect function
        async def stateful_build_side_effect(previously_designed):
            # Capture a deep copy of the arguments at this exact moment.
            captured_args_history.append(copy.deepcopy(previously_designed))

            # Return a unique response for each call to simulate the real process.
            call_num = len(captured_args_history)
            return {"key_piece": {"name": f"Garment {call_num}"}}

        mock_instance.build = AsyncMock(side_effect=stateful_build_side_effect)

        mocker.patch(
            "catalyst.pipeline.processors.synthesis.SingleGarmentBuilder",
            return_value=mock_instance,
        )
        return mock_instance, captured_args_history

    # --- END: THE DEFINITIVE, ROBUST MOCK FIX ---

    async def test_process_success_and_sequential_logic(
        self, run_context: RunContext, mock_garment_builder
    ):
        """Verify the builder is called 3 times and correctly passes the list of previously designed garments."""
        # Arrange
        mock_builder_instance, captured_args = mock_garment_builder
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()

        # Act
        context = await processor.process(run_context)

        # Assert
        assert mock_builder_instance.build.call_count == 3
        assert len(context.final_report["detailed_key_pieces"]) == 3

        # Assert against our explicit, immutable record of the calls.
        assert len(captured_args) == 3
        assert captured_args[0] == []  # Call 1 received an empty list
        assert (
            len(captured_args[1]) == 1 and captured_args[1][0]["name"] == "Garment 1"
        )  # Call 2
        assert (
            len(captured_args[2]) == 2 and captured_args[2][1]["name"] == "Garment 2"
        )  # Call 3

    async def test_process_handles_partial_failure(
        self, run_context: RunContext, mock_garment_builder
    ):
        """Verify it correctly handles a case where one garment generation fails."""
        mock_builder_instance, _ = mock_garment_builder
        mock_builder_instance.build.side_effect = [
            {"key_piece": {"name": "Garment 1"}},
            None,  # Simulate a failure on the second call
            {"key_piece": {"name": "Garment 3"}},
        ]
        run_context.structured_research_context = {"key": "value"}
        processor = KeyGarmentsProcessor()

        # Act
        context = await processor.process(run_context)

        # Assert
        assert mock_builder_instance.build.call_count == 3
        assert len(context.final_report["detailed_key_pieces"]) == 2
        assert context.final_report["detailed_key_pieces"][0]["name"] == "Garment 1"
        assert context.final_report["detailed_key_pieces"][1]["name"] == "Garment 3"
