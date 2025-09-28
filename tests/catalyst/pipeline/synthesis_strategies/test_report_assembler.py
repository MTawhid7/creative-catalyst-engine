# tests/catalyst/pipeline/synthesis_strategies/test_report_assembler.py

import pytest
from pathlib import Path
from pydantic import ValidationError

from catalyst.context import RunContext
from catalyst.pipeline.synthesis_strategies.report_assembler import ReportAssembler
from catalyst.models.trend_report import FashionTrendReport, PromptMetadata
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def run_context() -> RunContext:
    """Provides a fresh RunContext with a pre-populated initial brief."""
    context = RunContext(user_passage="test", results_dir=Path("dummy"))
    # --- START: THE DEFINITIVE FIX ---
    # The enriched_brief must contain all the fields that the assembler backfills.
    context.enriched_brief = {
        "season": "Spring/Summer",
        "year": 2025,
        "region": "Global",
        "target_gender": "Unisex",
        "target_age_group": "25-40",
        "target_model_ethnicity": "Any",
        "desired_mood": ["Test Mood"],  # This was the missing key
    }
    # --- END: THE DEFINITIVE FIX ---
    context.antagonist_synthesis = "A test synthesis"
    return context


@pytest.fixture
def report_data_from_builders() -> dict:
    """Simulates a valid, but incomplete, report dictionary from the builders."""
    return {
        "overarching_theme": "Test Theme",
        "trend_narrative_synthesis": "A test narrative.",
        "detailed_key_pieces": [],
    }


class TestReportAssembler:
    """Comprehensive tests for the ReportAssembler class."""

    def test_finalize_and_validate_report_success(
        self, run_context, report_data_from_builders
    ):
        assembler = ReportAssembler(run_context)
        final_report = assembler._finalize_and_validate_report(
            report_data_from_builders
        )

        assert final_report is not None
        assert final_report["season"] == ["Spring/Summer"]
        assert final_report["desired_mood"] == ["Test Mood"]  # Verify backfill

    def test_finalize_and_validate_report_failure(self, run_context):
        invalid_data = {
            "detailed_key_pieces": "this is a string, not a list",
        }
        assembler = ReportAssembler(run_context)
        final_report = assembler._finalize_and_validate_report(invalid_data)
        assert final_report is None

    @pytest.mark.asyncio
    async def test_assemble_from_fallback_async_success(self, run_context, mocker):
        mock_ai_response = FashionTrendReport(
            prompt_metadata=PromptMetadata(run_id="temp", user_passage="temp"),
            overarching_theme="Fallback Theme",
            season=["FW"],
            year=[2026],
            region=["Test"],
            target_gender="Test",
            target_age_group="Test",
            target_model_ethnicity="Test",
            antagonist_synthesis="Fallback synthesis",
        )
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.report_assembler.invoke_with_resilience",
            return_value=mock_ai_response,
        )
        assembler = ReportAssembler(run_context)
        fallback_report = await assembler._assemble_from_fallback_async()
        assert fallback_report is not None

    @pytest.mark.asyncio
    async def test_assemble_from_fallback_async_failure(self, run_context, mocker):
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.report_assembler.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        assembler = ReportAssembler(run_context)
        fallback_report = await assembler._assemble_from_fallback_async()
        assert fallback_report is None
