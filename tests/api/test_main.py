# tests/api/test_main.py

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient
from arq.jobs import Job, JobStatus

from api.main import app
from api.services.streaming import create_event_generator


@pytest.fixture
def mock_arq_redis() -> AsyncMock:
    """Provides a mock ARQ Redis client."""
    return AsyncMock()


class TestJobSubmissionEndpoint:
    """Tests for the POST /v1/creative-jobs endpoint."""

    def test_submit_job_success(self, mock_arq_redis: AsyncMock, mocker):
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_job = MagicMock(job_id="test_job_123")
        mock_arq_redis.enqueue_job.return_value = mock_job

        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json={"user_passage": "test"})
            assert response.status_code == 202
            assert response.json()["job_id"] == "test_job_123"

    def test_submit_job_failure(self, mock_arq_redis: AsyncMock, mocker):
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_arq_redis.enqueue_job.return_value = None

        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json={"user_passage": "test"})
            assert response.status_code == 500


@pytest.mark.asyncio
class TestEventGeneratorLogic:
    """Tests the core async generator logic directly."""

    @pytest.fixture(autouse=True)
    def mock_sleep(self, mocker):
        """Auto-mock asyncio.sleep to prevent any actual pausing."""
        return mocker.patch(
            "api.services.streaming.asyncio.sleep", new_callable=AsyncMock
        )

    # --- START: THE DEFINITIVE, SIMPLIFIED FIX ---
    async def test_stream_generator_yields_final_result_on_complete(
        self, mock_arq_redis: AsyncMock, mocker
    ):
        """
        Verify the generator yields the correct final result when a job is complete.
        This is the most critical success path.
        """
        # Arrange
        final_result = {"report": "done"}

        # Simulate a job that is already complete
        mock_job_instance = AsyncMock()
        mock_job_instance.status.return_value = JobStatus.complete
        mock_job_instance.result.return_value = final_result
        mocker.patch("api.services.streaming.Job", return_value=mock_job_instance)

        # Act
        results = [
            item
            async for item in create_event_generator("test_job_123", mock_arq_redis)
        ]

        # Assert
        assert len(results) == 1  # Should yield only the final 'complete' event
        complete_event = results[0]
        assert complete_event["event"] == "complete"
        complete_data = json.loads(complete_event["data"])
        assert complete_data["status"] == "complete"
        assert complete_data["result"] == final_result

    # --- END: THE DEFINITIVE, SIMPLIFIED FIX ---

    async def test_stream_generator_job_not_found(
        self, mock_arq_redis: AsyncMock, mocker
    ):
        """Verify the generator yields an error event if the job is not found."""
        mock_job_instance = AsyncMock(
            status=AsyncMock(return_value=JobStatus.not_found)
        )
        mocker.patch("api.services.streaming.Job", return_value=mock_job_instance)

        results = [
            item async for item in create_event_generator("not_found", mock_arq_redis)
        ]

        assert len(results) == 1
        assert results[0]["event"] == "error"
