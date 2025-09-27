# tests/catalyst/pipeline/processors/test_reporting.py

import pytest
import json
import asyncio  # <-- FIX 1: Import asyncio
from pathlib import Path

from catalyst.context import RunContext
from catalyst.pipeline.processors.reporting import FinalOutputGeneratorProcessor
from catalyst.models.trend_report import (
    FashionTrendReport,
    PromptMetadata,
    KeyPieceDetail,
)


@pytest.fixture
def valid_run_context(tmp_path: Path) -> RunContext:
    """Provides a RunContext with a valid, populated final_report."""
    report_model = FashionTrendReport(
        prompt_metadata=PromptMetadata(run_id="test-run", user_passage="test"),
        detailed_key_pieces=[
            KeyPieceDetail(key_piece_name="The Quantum Weave Jacket"),
            KeyPieceDetail(key_piece_name="The Chronos Trouser"),
        ],
        season=["FW"],
        year=[2025],
        region=["Global"],
        target_gender="Unisex",
        target_age_group="25-40",
        target_model_ethnicity="Any",
        antagonist_synthesis="test",
    )
    context = RunContext(user_passage="test", results_dir=tmp_path)
    context.final_report = report_model.model_dump(mode="json")
    context.structured_research_context = {"trend_narrative": "A test narrative."}
    return context


@pytest.mark.asyncio
class TestFinalOutputGeneratorProcessor:
    """Comprehensive tests for the FinalOutputGeneratorProcessor."""

    async def test_process_happy_path(self, valid_run_context: RunContext, mocker):
        """
        Verify that on a successful run, prompts are generated, injected,
        and both the report and prompts files are saved correctly.
        """
        # Arrange: Mock the PromptGenerator and its output
        mock_prompts = {
            "The Quantum Weave Jacket": {
                "mood_board": "mood_board_prompt_jacket",
                "final_garment": "final_garment_prompt_jacket",
            }
        }

        # --- START: THE DEFINITIVE FIX ---
        # To mock an async method, we must return an awaitable (a Future).
        future = asyncio.Future()
        future.set_result(mock_prompts)
        mock_prompt_generator_instance = mocker.Mock()
        mock_prompt_generator_instance.generate_prompts.return_value = future
        # --- END: THE DEFINITIVE FIX ---

        mocker.patch(
            "catalyst.pipeline.processors.reporting.PromptGenerator",
            return_value=mock_prompt_generator_instance,
        )

        processor = FinalOutputGeneratorProcessor()

        # Act
        context = await processor.process(valid_run_context)

        # Assert: Check that the files were created
        results_dir = context.results_dir
        report_path = results_dir / "itemized_fashion_trends.json"
        prompts_path = results_dir / "generated_prompts.json"

        assert report_path.exists()
        assert prompts_path.exists()

        # Assert: Check the content of the prompts file
        with open(prompts_path, "r") as f:
            saved_prompts = json.load(f)
        assert saved_prompts == mock_prompts

        # Assert: Check that the prompts were correctly injected into the final report
        with open(report_path, "r") as f:
            saved_report = json.load(f)

        jacket_piece = saved_report["detailed_key_pieces"][0]
        trouser_piece = saved_report["detailed_key_pieces"][1]

        assert jacket_piece["key_piece_name"] == "The Quantum Weave Jacket"
        assert jacket_piece["mood_board_prompt"] == "mood_board_prompt_jacket"
        assert jacket_piece["final_garment_prompt"] == "final_garment_prompt_jacket"

        assert trouser_piece["mood_board_prompt"] is None
        assert trouser_piece["final_garment_prompt"] is None

    async def test_process_raises_error_on_empty_report(self, tmp_path: Path):
        """
        Verify that the processor fails fast if the context's final_report is empty.
        """
        context = RunContext(user_passage="test", results_dir=tmp_path)
        context.final_report = {}
        processor = FinalOutputGeneratorProcessor()

        with pytest.raises(
            ValueError, match="Cannot generate outputs without a final report."
        ):
            await processor.process(context)

    async def test_process_handles_prompt_generation_failure_gracefully(
        self, valid_run_context: RunContext, mocker
    ):
        """
        Verify that if prompt generation fails, the main report is still saved.
        """
        # Arrange: Mock the PromptGenerator to raise an exception
        mocker.patch(
            "catalyst.pipeline.processors.reporting.PromptGenerator.generate_prompts",
            side_effect=Exception("Simulated prompt generation failure"),
        )
        processor = FinalOutputGeneratorProcessor()

        # Act
        context = await processor.process(valid_run_context)

        # Assert
        results_dir = context.results_dir
        report_path = results_dir / "itemized_fashion_trends.json"
        prompts_path = results_dir / "generated_prompts.json"

        assert report_path.exists()
        assert not prompts_path.exists()

        with open(report_path, "r") as f:
            saved_report = json.load(f)
        assert saved_report["detailed_key_pieces"][0]["mood_board_prompt"] is None
