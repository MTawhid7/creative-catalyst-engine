# tests/api/test_worker.py

import pytest
from unittest.mock import AsyncMock, patch

# Import the function we are testing
from api.worker import create_creative_report

# Define paths to the functions we need to mock
RUN_PIPELINE_PATH = "api.worker.run_pipeline"
GET_CACHE_PATH = "api.worker.get_from_l0_cache"
SET_CACHE_PATH = "api.worker.set_in_l0_cache"
PUBLISH_STATUS_PATH = "api.worker._publish_status"
CLEANUP_PATH = "api.worker.cleanup_old_results"


@pytest.fixture
def mock_arq_context():
    """Provides a mock ARQ context dictionary, including a mock redis client."""
    return {"redis": AsyncMock(), "job_id": "test_job_123"}


@pytest.fixture
def mock_final_report():
    """Provides a sample final_report dictionary, as if from the pipeline."""
    return {
        "detailed_key_pieces": [
            {
                "key_piece_name": "Test Piece",
                "final_garment_relative_path": "results/temp/image.png",
            }
        ]
    }


@pytest.mark.asyncio
async def test_create_creative_report_cache_miss(
    mocker, mock_arq_context, mock_final_report
):
    """
    Tests the primary success path: a cache miss, followed by a full pipeline run,
    URL injection, and caching the new result.
    """
    # ARRANGE
    # Mock all dependencies
    mocker.patch(PUBLISH_STATUS_PATH)
    mock_cleanup = mocker.patch(CLEANUP_PATH)
    mock_get_cache = mocker.patch(GET_CACHE_PATH, return_value=None)
    mock_set_cache = mocker.patch(SET_CACHE_PATH)
    mock_run_pipeline = mocker.patch(RUN_PIPELINE_PATH)

    # Configure the mock run_pipeline to populate the context with a report
    async def pipeline_side_effect(context):
        context.final_report = mock_final_report
        # Simulate the finalization step renaming the directory
        context.results_dir = context.results_dir.parent / "final_dir_name"
        return context

    mock_run_pipeline.side_effect = pipeline_side_effect

    # ACT
    result = await create_creative_report(mock_arq_context, "a new prompt")

    # ASSERT
    # 1. Verify the correct sequence of calls.
    mock_cleanup.assert_called_once()
    mock_get_cache.assert_called_once()
    mock_run_pipeline.assert_called_once()
    mock_set_cache.assert_called_once()

    # 2. Verify the URL injection worked.
    final_piece = result["final_report"]["detailed_key_pieces"][0]
    assert "final_garment_image_url" in final_piece
    assert (
        "http://127.0.0.1:9500/results/final_dir_name/image.png"
        in final_piece["final_garment_image_url"]
    )


@pytest.mark.asyncio
async def test_create_creative_report_cache_hit(mocker, mock_arq_context):
    """
    Tests the cache hit path: the function should return the cached result
    immediately and not run the pipeline.
    """
    # ARRANGE
    cached_data = {"final_report": "previously cached data"}
    mocker.patch(PUBLISH_STATUS_PATH)
    mock_cleanup = mocker.patch(CLEANUP_PATH)
    mock_get_cache = mocker.patch(GET_CACHE_PATH, return_value=cached_data)
    mock_set_cache = mocker.patch(SET_CACHE_PATH)
    mock_run_pipeline = mocker.patch(RUN_PIPELINE_PATH)

    # ACT
    result = await create_creative_report(mock_arq_context, "a prompt that was cached")

    # ASSERT
    # 1. Verify the result is exactly what the cache provided.
    assert result == cached_data

    # 2. Verify that expensive operations were SKIPPED.
    mock_run_pipeline.assert_not_called()
    mock_set_cache.assert_not_called()

    # 3. Verify cleanup still runs.
    mock_cleanup.assert_called_once()
