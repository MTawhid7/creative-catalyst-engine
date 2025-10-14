# tests/catalyst/pipeline/synthesis_strategies/test_report_assembler.py

import pytest
from pathlib import Path

from catalyst.context import RunContext
from catalyst.pipeline.synthesis_strategies.report_assembler import ReportAssembler
from catalyst.models.trend_report import FashionTrendReport, PromptMetadata
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def run_context() -> RunContext:
    """Provides a fresh RunContext for each test."""
    context = RunContext(user_passage="test", results_dir=Path("dummy"))
    context.enriched_brief = {"theme_hint": "Test Theme"}
    context.brand_ethos = "Test Ethos"
    return context


@pytest.mark.asyncio
class TestReportAssemblerFallback:
    """
    Tests for the ReportAssembler's sole responsibility: the fallback synthesis path.
    """

    async def test_assemble_from_fallback_async_success(self, run_context, mocker):
        """
        Verify that on a successful AI call, the fallback method returns the
        deserialized report data.
        """
        # Arrange
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

        # Act
        fallback_report = await assembler.assemble_from_fallback_async()

        # Assert
        assert fallback_report is not None
        assert fallback_report["overarching_theme"] == "Fallback Theme"

    @pytest.mark.asyncio
    async def test_assemble_from_fallback_async_failure(self, run_context, mocker):
        """
        Verify that if the AI call fails permanently, the fallback method
        returns None.
        """
        # Arrange
        mocker.patch(
            "catalyst.pipeline.synthesis_strategies.report_assembler.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        assembler = ReportAssembler(run_context)

        # Act
        fallback_report = await assembler.assemble_from_fallback_async()

        # Assert
        assert fallback_report is None
