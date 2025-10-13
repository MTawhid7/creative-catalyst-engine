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
    """Tests for the initial deconstruction step."""

    async def test_process_success(self, run_context: RunContext, mocker):
        # --- START: MODIFICATION ---
        # Mock now includes the new mandatory fields to create a valid model.
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
            generation_strategy="collection",
            explicit_garments=None,
        )
        # --- END: MODIFICATION ---

        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_brief,
        )
        processor = BriefDeconstructionProcessor()
        context = await processor.process(run_context)
        assert context.enriched_brief["theme_hint"] == "Test Theme"
        assert context.enriched_brief["generation_strategy"] == "collection"

    async def test_process_handles_ai_failure(self, run_context: RunContext, mocker):
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError()),
        )
        processor = BriefDeconstructionProcessor()
        with pytest.raises(ValueError):
            await processor.process(run_context)


# ... (The other test classes in this file remain unchanged) ...
@pytest.mark.asyncio
class TestConsolidatedBriefingProcessor:
    @pytest.fixture
    def initial_context(self, run_context: RunContext) -> RunContext:
        run_context.enriched_brief = {"theme_hint": "Initial Theme"}
        return run_context

    async def test_process_success(self, initial_context: RunContext, mocker):
        mock_response = ConsolidatedBriefingModel(
            ethos="Test Ethos", expanded_concepts=["c1"], search_keywords=["k1"]
        )
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_response,
        )
        processor = ConsolidatedBriefingProcessor()
        context = await processor.process(initial_context)
        assert context.brand_ethos == "Test Ethos"


@pytest.mark.asyncio
class TestCreativeAntagonistProcessor:
    @pytest.fixture
    def initial_context(self, run_context: RunContext) -> RunContext:
        run_context.enriched_brief = {"theme_hint": "Test Theme"}
        return run_context

    async def test_process_success(self, initial_context: RunContext, mocker):
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
