# tests/catalyst/pipeline/test_orchestrator.py

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from catalyst.context import RunContext
from catalyst.pipeline.orchestrator import PipelineOrchestrator

# Define paths to all the modules and classes the orchestrator uses
PROCESSOR_BASE_PATH = "catalyst.pipeline.orchestrator"
CACHE_MANAGER_PATH = f"{PROCESSOR_BASE_PATH}.cache_manager"
BRIEF_DECON_PATH = f"{PROCESSOR_BASE_PATH}.BriefDeconstructionProcessor"
ETHOS_CLAR_PATH = f"{PROCESSOR_BASE_PATH}.EthosClarificationProcessor"
BRIEF_ENRICH_PATH = f"{PROCESSOR_BASE_PATH}.BriefEnrichmentProcessor"
WEB_RESEARCH_PATH = f"{PROCESSOR_BASE_PATH}.WebResearchProcessor"
CONTEXT_STRUCT_PATH = f"{PROCESSOR_BASE_PATH}.ContextStructuringProcessor"
REPORT_SYNTH_PATH = f"{PROCESSOR_BASE_PATH}.ReportSynthesisProcessor"
FALLBACK_SYNTH_PATH = f"{PROCESSOR_BASE_PATH}.DirectKnowledgeSynthesisProcessor"
FINAL_OUTPUT_PATH = f"{PROCESSOR_BASE_PATH}.FinalOutputGeneratorProcessor"
IMAGE_GEN_PATH = f"{PROCESSOR_BASE_PATH}.get_image_generator"
SETTINGS_PATH = f"{PROCESSOR_BASE_PATH}.settings"


@pytest.fixture
def mock_processors(mocker):
    """Mocks all processor classes and returns their instances for assertion."""
    processors = {
        "brief_decon": mocker.patch(BRIEF_DECON_PATH).return_value,
        "ethos_clar": mocker.patch(ETHOS_CLAR_PATH).return_value,
        "brief_enrich": mocker.patch(BRIEF_ENRICH_PATH).return_value,
        "web_research": mocker.patch(WEB_RESEARCH_PATH).return_value,
        "context_struct": mocker.patch(CONTEXT_STRUCT_PATH).return_value,
        "report_synth": mocker.patch(REPORT_SYNTH_PATH).return_value,
        "fallback_synth": mocker.patch(FALLBACK_SYNTH_PATH).return_value,
        "final_output": mocker.patch(FINAL_OUTPUT_PATH).return_value,
        "image_gen": mocker.patch(IMAGE_GEN_PATH).return_value,
    }
    for name, proc in processors.items():
        # Make each mocked processor's process method an awaitable mock
        proc.process = AsyncMock(side_effect=lambda context: context)
    return processors


@pytest.fixture
def mock_cache_manager(mocker):
    """Mocks the cache_manager module."""
    return mocker.patch(CACHE_MANAGER_PATH)


@pytest.fixture
def run_context(tmp_path):
    """Provides a fresh RunContext for each test."""
    return RunContext(user_passage="test", results_dir=tmp_path)


@pytest.mark.asyncio
async def test_orchestrator_happy_path_with_cache_miss(
    mock_processors, mock_cache_manager, run_context
):
    """
    Tests the full, primary workflow when no cached result is found.
    """
    # ARRANGE
    mock_cache_manager.check_report_cache_async.return_value = None
    # Simulate ReportSynthesisProcessor successfully creating a report
    mock_processors["report_synth"].process = AsyncMock(
        side_effect=lambda context: setattr(context, "final_report", {"key": "value"})
        or context
    )

    orchestrator = PipelineOrchestrator()

    # ACT
    await orchestrator.run(run_context)

    # ASSERT
    # All primary path processors should have been called.
    assert mock_processors["brief_decon"].process.call_count == 1
    assert mock_processors["web_research"].process.call_count == 1
    assert mock_processors["report_synth"].process.call_count == 1
    assert mock_processors["image_gen"].process.call_count == 1
    # The fallback processor should NOT have been called.
    assert mock_processors["fallback_synth"].process.call_count == 0


@pytest.mark.asyncio
async def test_orchestrator_skips_synthesis_on_cache_hit(
    mock_processors, mock_cache_manager, run_context, mocker
):
    """
    Tests the critical path where a cache hit correctly skips expensive steps.
    """
    # ARRANGE
    mocker.patch("shutil.copytree")
    mock_cache_manager.check_report_cache_async = AsyncMock(
        return_value='{"cached_results_path": "folder", "final_report": {}}'
    )

    # --- START: THE DEFINITIVE FIX ---
    # Instead of mocking pathlib, we mock the 'settings' object that the
    # orchestrator itself will import and use.
    mock_settings = mocker.patch(SETTINGS_PATH)

    # Create a mock Path object that will be the return value for the directory.
    mock_source_path = MagicMock()
    mock_source_path.exists.return_value = True
    mock_source_path.is_dir.return_value = True

    # Configure the mocked ARTIFACT_CACHE_DIR so that when the '/' operator
    # is used on it, it returns our pre-configured mock_source_path.
    mock_settings.ARTIFACT_CACHE_DIR.__truediv__.return_value = mock_source_path
    # --- END: THE DEFINITIVE FIX ---

    orchestrator = PipelineOrchestrator()

    # ACT
    is_from_cache = await orchestrator.run(run_context)

    # ASSERT
    assert is_from_cache is True
    assert mock_processors["brief_decon"].process.call_count == 1

    assert mock_processors["web_research"].process.call_count == 0
    assert mock_processors["report_synth"].process.call_count == 0
    assert mock_processors["image_gen"].process.call_count == 0


@pytest.mark.asyncio
async def test_orchestrator_activates_fallback_path_on_failure(
    mock_processors, mock_cache_manager, run_context
):
    """
    Tests that if the primary ReportSynthesisProcessor fails (returns an empty
    report), the DirectKnowledgeSynthesisProcessor is activated.
    """
    # ARRANGE
    mock_cache_manager.check_report_cache_async.return_value = None
    # Simulate the primary processor failing by not populating final_report
    mock_processors["report_synth"].process = AsyncMock(
        side_effect=lambda context: setattr(context, "final_report", {}) or context
    )
    # Simulate the fallback processor SUCCEEDING
    mock_processors["fallback_synth"].process = AsyncMock(
        side_effect=lambda context: setattr(
            context, "final_report", {"fallback_key": "value"}
        )
        or context
    )

    orchestrator = PipelineOrchestrator()

    # ACT
    await orchestrator.run(run_context)

    # ASSERT
    assert mock_processors["report_synth"].process.call_count == 1
    # The fallback processor SHOULD have been called.
    assert mock_processors["fallback_synth"].process.call_count == 1
    # Subsequent steps should still run.
    assert mock_processors["image_gen"].process.call_count == 1
