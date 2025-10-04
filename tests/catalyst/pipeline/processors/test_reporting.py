# tests/catalyst/pipeline/processors/test_reporting.py

import pytest
import json
import asyncio
from pathlib import Path

from catalyst.context import RunContext
from catalyst.pipeline.processors.reporting import FinalOutputGeneratorProcessor
from catalyst.models.trend_report import (
    FashionTrendReport,
    PromptMetadata,
    KeyPieceDetail,
)

# --- CHANGE: Import the new ArtDirectionModel ---
from catalyst.pipeline.synthesis_strategies.synthesis_models import ArtDirectionModel


@pytest.fixture
def valid_run_context(tmp_path: Path) -> RunContext:
    # ... (fixture remains the same) ...
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
        # Arrange: Mock the PromptGenerator and its new tuple output
        mock_prompts = {
            "The Quantum Weave Jacket": {"final_garment": "final_garment_prompt_jacket"}
        }
        mock_art_direction = ArtDirectionModel(
            narrative_setting_description="A very specific test setting."
        )

        # --- CHANGE: Mock the generate_prompts method to return a future with the tuple ---
        future = asyncio.Future()
        future.set_result((mock_prompts, mock_art_direction))
        mock_prompt_generator_instance = mocker.Mock()
        mock_prompt_generator_instance.generate_prompts.return_value = future

        mocker.patch(
            "catalyst.pipeline.processors.reporting.PromptGenerator",
            return_value=mock_prompt_generator_instance,
        )

        processor = FinalOutputGeneratorProcessor()

        # Act
        context = await processor.process(valid_run_context)

        # Assert: Check that files were created
        report_path = context.results_dir / "itemized_fashion_trends.json"
        prompts_path = context.results_dir / "generated_prompts.json"
        assert report_path.exists()
        assert prompts_path.exists()

        # --- CHANGE: Add assertion to check for injected narrative setting ---
        with open(report_path, "r") as f:
            saved_report = json.load(f)
        assert (
            saved_report["narrative_setting_description"]
            == "A very specific test setting."
        )
        assert (
            saved_report["detailed_key_pieces"][0]["final_garment_prompt"]
            == "final_garment_prompt_jacket"
        )

    # ... (other tests for failure cases remain the same) ...
    async def test_process_raises_error_on_empty_report(self, tmp_path: Path):
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
        mocker.patch(
            "catalyst.pipeline.processors.reporting.PromptGenerator.generate_prompts",
            side_effect=Exception("Simulated failure"),
        )
        processor = FinalOutputGeneratorProcessor()
        context = await processor.process(valid_run_context)
        report_path = context.results_dir / "itemized_fashion_trends.json"
        prompts_path = context.results_dir / "generated_prompts.json"
        assert report_path.exists()
        assert not prompts_path.exists()
