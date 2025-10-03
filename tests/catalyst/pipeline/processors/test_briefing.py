# tests/catalyst/pipeline/processors/test_briefing.py

import pytest
from pathlib import Path
from unittest.mock import AsyncMock

from catalyst.context import RunContext
from catalyst.pipeline.processors.briefing import (
    BriefDeconstructionProcessor,
    ConsolidatedBriefingProcessor,
    CreativeAntagonistProcessor,
    StructuredBriefModel,
    ConsolidatedBriefingModel,
    AntagonistSynthesisModel,
)
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    """Provides a fresh RunContext for each test."""
    return RunContext(user_passage="A test passage.", results_dir=tmp_path)


@pytest.mark.asyncio
class TestBriefDeconstructionProcessor:
    """Tests for the initial deconstruction step (remains critical)."""

    async def test_process_success(self, run_context: RunContext, mocker):
        mock_brief = StructuredBriefModel(
            theme_hint="Test Theme",
            garment_type="Jacket",
            brand_category="Luxe",
            target_audience="All",
            region="Global",
            key_attributes=["A"],
            season="FW",
            year=2025,
            target_gender="Any",
            target_model_ethnicity="Any",
            target_age_group="All",
            desired_mood=["B"],
        )
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_brief,
        )
        processor = BriefDeconstructionProcessor()
        context = await processor.process(run_context)
        assert context.enriched_brief["theme_hint"] == "Test Theme"

    async def test_process_handles_ai_failure(self, run_context: RunContext, mocker):
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        processor = BriefDeconstructionProcessor()
        with pytest.raises(ValueError):
            await processor.process(run_context)


@pytest.mark.asyncio
class TestConsolidatedBriefingProcessor:
    """Tests for the new, efficient consolidated briefing processor."""

    @pytest.fixture
    def initial_context(self, run_context: RunContext) -> RunContext:
        run_context.enriched_brief = {"theme_hint": "Initial Theme"}
        return run_context

    async def test_process_success(self, initial_context: RunContext, mocker):
        """Verify a successful consolidated call populates all context fields."""
        mock_response = ConsolidatedBriefingModel(
            ethos="Test Ethos",
            expanded_concepts=["c1", "c2"],
            search_keywords=["k1", "k2"],
        )
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_response,
        )
        processor = ConsolidatedBriefingProcessor()
        context = await processor.process(initial_context)

        assert context.brand_ethos == "Test Ethos"
        assert context.enriched_brief["expanded_concepts"] == ["c1", "c2"]
        assert "k1" in context.enriched_brief["search_keywords"]
        assert "Initial Theme" in context.enriched_brief["search_keywords"]

    async def test_process_graceful_failure(self, initial_context: RunContext, mocker):
        """Verify that an AI failure results in safe default values."""
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        processor = ConsolidatedBriefingProcessor()
        context = await processor.process(initial_context)

        assert context.brand_ethos == ""
        assert context.enriched_brief["expanded_concepts"] == []


@pytest.mark.asyncio
class TestCreativeAntagonistProcessor:
    """Tests for the refactored, single-responsibility antagonist processor."""

    @pytest.fixture
    def initial_context(self, run_context: RunContext) -> RunContext:
        run_context.enriched_brief = {"theme_hint": "Test Theme"}
        run_context.brand_ethos = "Test Ethos"
        return run_context

    async def test_process_success(self, initial_context: RunContext, mocker):
        """Verify a successful call populates the antagonist_synthesis."""
        mock_response = AntagonistSynthesisModel(
            antagonist_synthesis="A creative twist."
        )
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_response,
        )
        processor = CreativeAntagonistProcessor()
        context = await processor.process(initial_context)
        assert context.antagonist_synthesis == "A creative twist."

    async def test_process_graceful_failure(self, initial_context: RunContext, mocker):
        """Verify that an AI failure results in a safe default value."""
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        processor = CreativeAntagonistProcessor()
        context = await processor.process(initial_context)
        assert context.antagonist_synthesis == ""
