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

    @pytest.fixture
    def mock_run_pipeline(self, mocker) -> AsyncMock:
        async def side_effect(context: RunContext):
            context.final_report = {
                "detailed_key_pieces": [{"key_piece_name": "Test Jacket"}]
            }
            context.is_complete = True
            return context

        return mocker.patch("api.worker.run_pipeline", side_effect=side_effect)

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_happy_path_cache_miss(
        self, seed: int, mock_context, mock_run_pipeline, mocker
    ):
        """Verify a full, successful run passes the seed correctly."""
        mock_get_cache = mocker.patch(
            "api.worker.get_from_l0_cache", new_callable=AsyncMock, return_value=None
        )
        mock_set_cache = mocker.patch(
            "api.worker.set_in_l0_cache", new_callable=AsyncMock
        )
        mocker.patch("api.worker.cleanup_old_results")

        # Act
        await create_creative_report(mock_context, "test passage", seed)

        # Assert
        mock_get_cache.assert_awaited_once_with(
            "test passage", seed, mock_context["redis"]
        )
        mock_run_pipeline.assert_awaited_once()
        # Get the context object that was passed to the pipeline
        passed_context = mock_run_pipeline.call_args[0][0]
        assert passed_context.variation_seed == seed
        mock_set_cache.assert_awaited_once()
        # Verify the seed was passed when setting the cache
        assert mock_set_cache.call_args[0][1] == seed

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_happy_path_cache_hit(self, seed: int, mock_context, mocker):
        """Verify a cache hit correctly uses the seed."""
        cached_data = {"final_report": {"overarching_theme": "Cached Theme"}}
        mock_get_cache = mocker.patch(
            "api.worker.get_from_l0_cache",
            new_callable=AsyncMock,
            return_value=cached_data,
        )
        mock_run_pipeline = mocker.patch(
            "api.worker.run_pipeline", new_callable=AsyncMock
        )
        mocker.patch("api.worker.cleanup_old_results")

        result = await create_creative_report(mock_context, "test passage", seed)

        assert result == cached_data
        mock_get_cache.assert_awaited_once_with(
            "test passage", seed, mock_context["redis"]
        )
        mock_run_pipeline.assert_not_called()

    # The failure tests don't need parametrization as the seed doesn't affect the failure path
    async def test_pipeline_failure(self, mock_context, mocker):
        mocker.patch("api.worker.get_from_l0_cache", return_value=None)
        mocker.patch(
            "api.worker.run_pipeline", side_effect=ValueError("Pipeline Error")
        )
        mocker.patch("api.worker.cleanup_old_results")
        with pytest.raises(ValueError, match="Pipeline Error"):
            await create_creative_report(mock_context, "test passage", 0)
