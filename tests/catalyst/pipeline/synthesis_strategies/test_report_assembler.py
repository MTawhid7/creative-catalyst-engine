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
    context.enriched_brief = {
        "season": "Spring/Summer",
        "year": 2025,
        "region": "Global",
        "target_gender": "Unisex",
        "target_age_group": "25-40",
        "target_model_ethnicity": "Any",
    }
    context.antagonist_synthesis = "A test synthesis"
    return context


@pytest.fixture
def report_data_from_builders() -> dict:
    """Simulates a valid, but incomplete, report dictionary from the builders."""
    return {
        "overarching_theme": "Test Theme",
        "trend_narrative_synthesis": "A test narrative.",
        "detailed_key_pieces": [],  # Must be present, even if empty
    }


class TestReportAssembler:
    """Comprehensive tests for the ReportAssembler class."""

    def test_finalize_and_validate_report_success(
        self, run_context, report_data_from_builders
    ):
        """
        Verify that the primary path correctly backfills data from the brief,
        adds metadata, and successfully validates the final report.
        """
        assembler = ReportAssembler(run_context)
        final_report = assembler._finalize_and_validate_report(
            report_data_from_builders
        )

        assert final_report is not None
        assert final_report["season"] == ["Spring/Summer"]
        assert final_report["year"] == [2025]

    def test_finalize_and_validate_report_failure(self, run_context):
        """
        Verify that the function returns None if the final data fails validation
        due to an unrecoverable type error.
        """
        # --- START: THE DEFINITIVE FIX ---
        # This data is now truly invalid. The 'detailed_key_pieces' field is a string,
        # but the FashionTrendReport model strictly requires a List. The assembler has
        # no special logic to fix this, so Pydantic validation will fail.
        invalid_data = {
            "overarching_theme": "An incomplete theme",
            "detailed_key_pieces": "this is a string, not a list",  # This will cause the failure
        }
        # --- END: THE DEFINITIVE FIX ---

        assembler = ReportAssembler(run_context)
        final_report = assembler._finalize_and_validate_report(invalid_data)

        assert final_report is None

    @pytest.mark.asyncio
    async def test_assemble_from_fallback_async_success(self, run_context, mocker):
        """
        Verify that the fallback path correctly calls the AI and returns a
        finalized report.
        """
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
        assert fallback_report["overarching_theme"] == "Fallback Theme"

    @pytest.mark.asyncio
    async def test_assemble_from_fallback_async_failure(self, run_context, mocker):
        """
        Verify that the fallback path returns None if the AI call fails.
        """
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.report_assembler.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        assembler = ReportAssembler(run_context)
        fallback_report = await assembler._assemble_from_fallback_async()
        assert fallback_report is None
