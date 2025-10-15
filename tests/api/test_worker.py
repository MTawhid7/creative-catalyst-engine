# tests/api/test_worker.py

import pytest
from unittest.mock import AsyncMock, MagicMock, call, ANY
from pathlib import Path
import json

from api.worker import create_creative_report, regenerate_images_task
from catalyst.context import RunContext
from catalyst import settings


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
            # Simulate the final path renaming
            context.results_dir = Path(f"/app/results/20250101-120000_test-theme")
            return context

        return mocker.patch("api.worker.run_pipeline", side_effect=side_effect)

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_happy_path_cache_miss(
        self, seed: int, mock_context, mock_run_pipeline, mocker
    ):
        """Verify a full, successful run passes the seed and saves the results path."""
        mock_get_cache = mocker.patch(
            "api.worker.get_from_l0_cache", new_callable=AsyncMock, return_value=None
        )
        mock_set_cache = mocker.patch(
            "api.worker.set_in_l0_cache", new_callable=AsyncMock
        )
        mocker.patch("api.worker.cleanup_old_results")

        await create_creative_report(mock_context, "test passage", seed)

        mock_get_cache.assert_awaited_once_with(
            "test passage", seed, mock_context["redis"]
        )
        mock_run_pipeline.assert_awaited_once()

        # Verify the results path was saved to Redis
        mock_context["redis"].set.assert_any_call(
            f"job_results_path:{mock_context['job_id']}",
            "/app/results/20250101-120000_test-theme",
            ex=ANY,  # <-- Use the correctly imported ANY
        )
        mock_set_cache.assert_awaited_once()

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_happy_path_cache_hit(self, seed: int, mock_context, mocker):
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


@pytest.mark.asyncio
class TestRegenerateImagesTask:
    """Tests for the lightweight `regenerate_images_task`."""

    @pytest.fixture
    def mock_image_generator(self, mocker) -> MagicMock:
        mock_generator = MagicMock()
        mock_generator.process = AsyncMock(
            side_effect=lambda context, **kwargs: context
        )
        mocker.patch("api.worker.get_image_generator", return_value=mock_generator)
        return mock_generator

    @pytest.fixture
    def setup_mocks(self, mocker, tmp_path: Path):
        mocker.patch.object(settings, "RESULTS_DIR", tmp_path)
        original_dir = tmp_path / "original_run"
        original_dir.mkdir()
        (original_dir / settings.TREND_REPORT_FILENAME).write_text(
            json.dumps({"data": "report"})
        )
        (original_dir / settings.PROMPTS_FILENAME).write_text(
            json.dumps({"data": "prompts"})
        )
        mocker.patch("api.worker.shutil.copy")
        mocker.patch("api.worker.shutil.move")
        mocker.patch(
            "builtins.open",
            mocker.mock_open(read_data=json.dumps({"final_report": {}})),
        )
        return {"original_dir": original_dir}

    # --- START: THE DEFINITIVE TEST FIX ---
    async def test_regenerate_images_happy_path(
        self, mock_context, mock_image_generator, setup_mocks
    ):
        """Verify the regeneration task calls the image generator with correct overrides."""
        # Arrange
        original_job_id = "original_job_456"
        temp = 1.5
        mock_context["redis"].get.return_value = str(
            setup_mocks["original_dir"]
        ).encode()

        # Act: Call the task with the correct signature (no seed)
        await regenerate_images_task(mock_context, original_job_id, temp)

        # Assert
        mock_context["redis"].get.assert_awaited_once_with(
            f"job_results_path:{original_job_id}"
        )

        # Verify the image generator was called with only the temperature override
        mock_image_generator.process.assert_awaited_once()
        call_kwargs = mock_image_generator.process.call_args.kwargs
        assert "seed_override" not in call_kwargs
        assert call_kwargs["temperature_override"] == temp

    # --- END: THE DEFINITIVE TEST FIX ---
