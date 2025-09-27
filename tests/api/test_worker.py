# tests/api/test_worker.py

import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path

from api.worker import create_creative_report
from catalyst.context import RunContext


@pytest.fixture
def mock_context() -> dict:
    """Provides a mock ARQ context dictionary."""
    return {"redis": AsyncMock(), "job_id": "test_job_123"}


@pytest.mark.asyncio
class TestCreateCreativeReport:
    """Comprehensive tests for the main ARQ task `create_creative_report`."""

    # --- START: THE DEFINITIVE FIX ---
    @pytest.fixture
    def mock_run_pipeline(self, mocker) -> AsyncMock:
        """
        Mocks the run_pipeline function to simulate a successful run by
        modifying the context object passed to it, just like the real function.
        """

        async def side_effect(context: RunContext):
            # Simulate a successful pipeline run by populating the report
            context.final_report = {
                "detailed_key_pieces": [
                    {
                        "key_piece_name": "Test Jacket",
                        "final_garment_relative_path": f"results/{context.run_id}/test-jacket.png",
                    }
                ]
            }
            context.is_complete = True
            return context

        return mocker.patch("api.worker.run_pipeline", side_effect=side_effect)

    # --- END: THE DEFINITIVE FIX ---

    async def test_happy_path_cache_miss(self, mock_context, mock_run_pipeline, mocker):
        """
        Verify a full, successful run when the L0 cache misses.
        """
        # Arrange
        mocker.patch(
            "api.worker.get_from_l0_cache", new_callable=AsyncMock, return_value=None
        )
        mock_set_cache = mocker.patch(
            "api.worker.set_in_l0_cache", new_callable=AsyncMock
        )
        mock_publish_status = mocker.patch(
            "api.worker._publish_status", new_callable=AsyncMock
        )
        mocker.patch("api.worker.cleanup_old_results")

        # Act
        result = await create_creative_report(mock_context, "test passage")

        # Assert
        mock_run_pipeline.assert_awaited_once()
        mock_publish_status.assert_awaited_once()
        mock_set_cache.assert_awaited_once()

        assert (
            "final_garment_image_url"
            in result["final_report"]["detailed_key_pieces"][0]
        )

    async def test_happy_path_cache_hit(self, mock_context, mocker):
        """
        Verify the worker exits early and returns cached data on an L0 cache hit.
        """
        cached_data = {"final_report": {"overarching_theme": "Cached Theme"}}
        mocker.patch(
            "api.worker.get_from_l0_cache",
            new_callable=AsyncMock,
            return_value=cached_data,
        )
        mock_run_pipeline = mocker.patch(
            "api.worker.run_pipeline", new_callable=AsyncMock
        )
        mocker.patch("api.worker.cleanup_old_results")

        result = await create_creative_report(mock_context, "test passage")

        assert result == cached_data
        mock_run_pipeline.assert_not_called()

    async def test_pipeline_failure(self, mock_context, mocker):
        """
        Verify that if run_pipeline fails, the exception is propagated.
        """
        mocker.patch(
            "api.worker.get_from_l0_cache", new_callable=AsyncMock, return_value=None
        )
        mocker.patch(
            "api.worker.run_pipeline",
            new_callable=AsyncMock,
            side_effect=ValueError("Pipeline Error"),
        )
        mocker.patch("api.worker.cleanup_old_results")

        with pytest.raises(ValueError, match="Pipeline Error"):
            await create_creative_report(mock_context, "test passage")

    async def test_empty_report_failure(self, mock_context, mocker):
        """
        Verify that if the pipeline returns an empty report, a RuntimeError is raised.
        """

        # Arrange: Simulate a run that completes but leaves the report empty
        async def side_effect_empty(context: RunContext):
            context.final_report = {}
            context.is_complete = True
            return context

        mocker.patch(
            "api.worker.get_from_l0_cache", new_callable=AsyncMock, return_value=None
        )
        mocker.patch("api.worker.run_pipeline", side_effect=side_effect_empty)
        mocker.patch("api.worker.cleanup_old_results")

        with pytest.raises(
            RuntimeError, match="Pipeline finished but the final report is empty."
        ):
            await create_creative_report(mock_context, "test passage")
