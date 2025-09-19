# tests/catalyst/test_main_pipeline.py

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from catalyst.main import run_pipeline
from catalyst.context import RunContext
from catalyst import settings  # <-- FIX 1: Import the application settings

# Define paths to the modules we need to mock
ORCHESTRATOR_PATH = "catalyst.main.PipelineOrchestrator"
CACHE_MANAGER_PATH = "catalyst.main.cache_manager"
SHUTIL_PATH = "catalyst.main.shutil"
OS_PATH = "catalyst.main.os"


@pytest.fixture
def mock_main_dependencies(mocker):
    """Mocks all external dependencies for the run_pipeline function and returns them."""
    mock_deps = {
        "cache_manager": mocker.patch(CACHE_MANAGER_PATH),
        "shutil": mocker.patch(SHUTIL_PATH),
        "os": mocker.patch(OS_PATH),
        "orchestrator": mocker.patch(ORCHESTRATOR_PATH).return_value,
    }

    mock_deps["cache_manager"]._create_semantic_key.return_value = (
        "a-valid-semantic-key"
    )
    mock_deps["cache_manager"].add_to_report_cache_async = AsyncMock()

    async def mock_run(context):
        context.final_report = {"key": "value"}
        context.theme_slug = "test-slug"
        context.enriched_brief = {"theme_hint": "A test"}
        return False

    mock_deps["orchestrator"].run = AsyncMock(side_effect=mock_run)
    return mock_deps


@pytest.mark.asyncio
async def test_run_pipeline_finalization_logic(mock_main_dependencies, tmp_path: Path):
    """
    Tests that the run_pipeline function correctly renames the results directory,
    creates the symlink, and caches the artifacts after a successful run.
    """
    # ARRANGE
    context = RunContext(user_passage="test", results_dir=tmp_path)
    initial_temp_dir = context.results_dir
    initial_temp_dir.mkdir()

    # ACT
    final_context = await run_pipeline(context)

    # ASSERT
    # 1. Verify the orchestrator was run.
    mock_main_dependencies["orchestrator"].run.assert_called_once()

    # 2. Verify the 'move' command was called.
    mock_main_dependencies["shutil"].move.assert_called_once()

    # --- START: THE DEFINITIVE FIX ---
    # 3. Verify the final context path was updated to the application's
    #    configured RESULTS_DIR, not the temporary path.
    assert final_context.results_dir.parent == settings.RESULTS_DIR
    assert "test-slug" in final_context.results_dir.name
    # --- END: THE DEFINITIVE FIX ---

    # 4. Verify that the other file system operations were called.
    mock_main_dependencies["os"].symlink.assert_called_once()
    mock_main_dependencies["shutil"].copytree.assert_called_once()
    mock_main_dependencies[
        "cache_manager"
    ].add_to_report_cache_async.assert_called_once()
