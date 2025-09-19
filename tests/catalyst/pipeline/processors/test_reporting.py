# tests/catalyst/pipeline/processors/test_reporting.py

import pytest
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

from catalyst.context import RunContext
from catalyst.models.trend_report import FashionTrendReport
from catalyst.pipeline.processors.reporting import FinalOutputGeneratorProcessor

# Path to the PromptGenerator class we need to mock
PROMPT_GENERATOR_PATH = "catalyst.pipeline.processors.reporting.PromptGenerator"


@pytest.fixture
def full_trend_report() -> FashionTrendReport:
    """Loads a realistic trend report from the fixtures directory."""
    report_path = (
        Path(__file__).parent.parent.parent.parent
        / "fixtures"
        / "expected_final_report.json"
    )
    with open(report_path, "r") as f:
        data = json.load(f)
    return FashionTrendReport.model_validate(data)


@pytest.fixture
def run_context(tmp_path: Path, full_trend_report: FashionTrendReport) -> RunContext:
    """Provides a fresh RunContext with a populated final_report."""
    context = RunContext(user_passage="A test passage", results_dir=tmp_path)
    context.final_report = full_trend_report.model_dump(mode="json")
    return context


@pytest.mark.asyncio
async def test_final_output_generator_happy_path(mocker, run_context):
    """
    Tests that the processor successfully generates prompts, injects them,
    and saves the final report and prompts JSON files.
    """
    # ARRANGE
    # Mock all dependencies BEFORE the action.
    mock_prompt_generator_class = mocker.patch(PROMPT_GENERATOR_PATH)
    mock_prompt_generator_instance = MagicMock()
    mock_prompt_generator_instance.generate_prompts = AsyncMock(
        return_value={
            "The Heritage Drape Blazer": {
                "mood_board": "mood board prompt",
                "final_garment": "final garment prompt",
            }
        }
    )
    mock_prompt_generator_class.return_value = mock_prompt_generator_instance

    # Mock the built-in 'open' function to monitor file saves.
    open_mock = mocker.patch("builtins.open", mocker.mock_open())

    processor = FinalOutputGeneratorProcessor()

    # ACT
    # Call the processor only once.
    context = await processor.process(run_context)

    # ASSERT
    # 1. Verify prompt generation and injection.
    mock_prompt_generator_instance.generate_prompts.assert_called_once()
    first_piece = context.final_report["detailed_key_pieces"][0]
    assert first_piece["mood_board_prompt"] == "mood board prompt"

    # 2. Verify that two files were saved.
    assert open_mock.call_count == 2
    call_args_list = open_mock.call_args_list
    filenames = [call.args[0].name for call in call_args_list]
    assert "generated_prompts.json" in filenames
    assert "itemized_fashion_trends.json" in filenames


@pytest.mark.asyncio
async def test_final_output_generator_raises_error_on_empty_report(run_context):
    """
    Tests that the processor raises a ValueError if the final_report in the
    context is empty, which is a critical failure.
    """
    # ARRANGE
    run_context.final_report = {}
    processor = FinalOutputGeneratorProcessor()

    # ACT & ASSERT
    with pytest.raises(
        ValueError, match="Cannot generate outputs without a final report."
    ):
        await processor.process(run_context)
