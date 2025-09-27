# tests/catalyst/pipeline/processors/test_briefing.py

import pytest
from pathlib import Path
from unittest.mock import MagicMock

from catalyst.context import RunContext
from catalyst.pipeline.processors.briefing import (
    BriefDeconstructionProcessor,
    EthosClarificationProcessor,
    BriefEnrichmentProcessor,
    StructuredBriefModel,
    EthosModel,
    ConceptsModel,
    AntagonistSynthesisModel,
    KeywordsModel,
)
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def run_context(tmp_path: Path) -> RunContext:
    """Provides a fresh RunContext for each test."""
    return RunContext(
        user_passage="A test passage about luxury denim.", results_dir=tmp_path
    )


@pytest.mark.asyncio
class TestBriefDeconstructionProcessor:
    # ... (this class is unchanged and correct)
    async def test_process_success(self, run_context: RunContext, mocker):
        mock_brief = StructuredBriefModel(
            theme_hint="Luxury Denim Craft",
            garment_type="Jeans",
            brand_category="Haute Couture",
            target_audience="Affluent collectors",
            region="Global",
            key_attributes=["Artisanal", "Bespoke"],
            season="auto",
            year="auto",
            target_gender="Female",
            target_model_ethnicity="Japanese",
            target_age_group="Adult (30-50)",
            desired_mood=["Elegant", "Textured"],
        )
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_brief,
        )
        processor = BriefDeconstructionProcessor()
        context = await processor.process(run_context)
        assert context.enriched_brief["theme_hint"] == "Luxury Denim Craft"
        assert context.theme_slug == "luxury-denim-cr"
        assert context.enriched_brief["season"] != "auto"
        assert isinstance(context.enriched_brief["year"], str)

    async def test_process_handles_ai_failure(self, run_context: RunContext, mocker):
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        processor = BriefDeconstructionProcessor()
        with pytest.raises(ValueError, match="Brief deconstruction failed permanently"):
            await processor.process(run_context)


@pytest.mark.asyncio
class TestEthosClarificationProcessor:
    # ... (this class is unchanged and correct)
    async def test_process_success(self, run_context: RunContext, mocker):
        mock_ethos = EthosModel(ethos="A commitment to artisanal craft.")
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            return_value=mock_ethos,
        )
        processor = EthosClarificationProcessor()
        context = await processor.process(run_context)
        assert context.brand_ethos == "A commitment to artisanal craft."

    async def test_process_graceful_failure(self, run_context: RunContext, mocker):
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        processor = EthosClarificationProcessor()
        context = await processor.process(run_context)
        assert context.brand_ethos == ""


@pytest.mark.asyncio
class TestBriefEnrichmentProcessor:
    """Tests for the concurrent enrichment step."""

    @pytest.fixture
    def initial_context(self, run_context: RunContext) -> RunContext:
        """Provides a context that has already been through deconstruction."""
        run_context.enriched_brief = {
            "theme_hint": "Test Theme",
            "garment_type": "Jacket",
            "key_attributes": ["one", "two"],
            "search_keywords": ["initial_keyword"],
        }
        run_context.brand_ethos = "Test Ethos"
        return run_context

    async def test_process_success_all_calls(self, initial_context: RunContext, mocker):
        # ... (this test is unchanged and correct)
        mock_responses = {
            ConceptsModel: ConceptsModel(concepts=["concept1", "concept2"]),
            AntagonistSynthesisModel: AntagonistSynthesisModel(
                antagonist_synthesis="A creative twist."
            ),
            KeywordsModel: KeywordsModel(keywords=["keyword1", "keyword2"]),
        }
        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=lambda _, __, response_schema, **kwargs: mock_responses[
                response_schema
            ],
        )
        processor = BriefEnrichmentProcessor()
        context = await processor.process(initial_context)
        assert context.antagonist_synthesis == "A creative twist."
        assert context.enriched_brief["expanded_concepts"] == ["concept1", "concept2"]
        assert "initial_keyword" in context.enriched_brief["search_keywords"]
        assert "keyword1" in context.enriched_brief["search_keywords"]
        assert len(context.enriched_brief["search_keywords"]) == 4

    # --- START: THE DEFINITIVE FIX ---
    # The mock is simplified and the assertions are updated to reflect the new,
    # more resilient behavior of the source code.
    async def test_process_handles_partial_failure(
        self, initial_context: RunContext, mocker
    ):
        """Verify it proceeds gracefully if some non-critical AI calls fail."""
        # Arrange: A more robust mock that returns a value based on the schema requested.
        mock_responses = {
            ConceptsModel: MaxRetriesExceededError(ValueError("AI failed")),
            AntagonistSynthesisModel: AntagonistSynthesisModel(
                antagonist_synthesis="A creative twist."
            ),
            KeywordsModel: KeywordsModel(
                keywords=["keyword1"]
            ),  # Note: This won't be called if concepts fails
        }

        async def mock_invoke(ai_function, prompt, response_schema, **kwargs):
            result = mock_responses[response_schema]
            if isinstance(result, Exception):
                raise result
            return result

        mocker.patch(
            "catalyst.pipeline.processors.briefing.invoke_with_resilience",
            side_effect=mock_invoke,
        )
        processor = BriefEnrichmentProcessor()

        # Act
        context = await processor.process(initial_context)

        # Assert
        assert context.antagonist_synthesis == "A creative twist."
        # Concepts list should be empty due to failure and safe default
        assert context.enriched_brief["expanded_concepts"] == []
        # Keywords should only contain the initial keywords, since the keywords call depends on concepts
        assert context.enriched_brief["search_keywords"] == [
            "Test Theme",
            "initial_keyword",
        ]

    # --- END: THE DEFINITIVE FIX ---
