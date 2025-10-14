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
    """Tests for the job submission endpoints."""

    @pytest.mark.parametrize(
        "payload, expected_seed",
        [
            ({"user_passage": "test"}, 0),
            ({"user_passage": "test", "variation_seed": 5}, 5),
        ],
    )
    def test_submit_job_success(
        self, payload: dict, expected_seed: int, mock_arq_redis: AsyncMock, mocker
    ):
        """Verify the main job is enqueued with the correct passage and seed."""
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_job = MagicMock(job_id="test_job_123")
        mock_arq_redis.enqueue_job.return_value = mock_job

        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json=payload)

            assert response.status_code == 202
            assert response.json()["job_id"] == "test_job_123"
            mock_arq_redis.enqueue_job.assert_awaited_once_with(
                "create_creative_report", payload["user_passage"], expected_seed
            )

    # --- START: NEW TEST FOR REGENERATION ENDPOINT ---
    def test_regenerate_images_success(self, mock_arq_redis: AsyncMock, mocker):
        """Verify the regeneration endpoint enqueues the correct task and arguments."""
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_arq_redis.exists.return_value = True  # Simulate original job exists
        mock_job = MagicMock(job_id="regen_job_789")
        mock_arq_redis.enqueue_job.return_value = mock_job

        with TestClient(app) as client:
            response = client.post(
                "/v1/creative-jobs/original_job_456/regenerate-images",
                json={"seed": 2, "temperature": 1.5},
            )
            assert response.status_code == 202
            assert response.json()["job_id"] == "regen_job_789"

            # Verify the correct task and arguments were enqueued
            mock_arq_redis.enqueue_job.assert_awaited_once_with(
                "regenerate_images_task",
                "original_job_456",
                2,
                1.5,
            )

    def test_regenerate_images_job_not_found(self, mock_arq_redis: AsyncMock, mocker):
        """Verify a 404 is returned if the original job does not exist."""
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_arq_redis.exists.return_value = False  # Simulate original job NOT found

        with TestClient(app) as client:
            response = client.post(
                "/v1/creative-jobs/nonexistent_job/regenerate-images", json={"seed": 1}
            )
            assert response.status_code == 404

    # --- END: NEW TEST FOR REGENERATION ENDPOINT ---

    def test_submit_job_failure(self, mock_arq_redis: AsyncMock, mocker):
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_arq_redis.enqueue_job.return_value = None
        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json={"user_passage": "test"})
            assert response.status_code == 500


@pytest.mark.asyncio
class TestEventGeneratorLogic:
    """Tests the core async generator logic directly."""

    # This test class remains unchanged.
    @pytest.fixture(autouse=True)
    def mock_sleep(self, mocker):
        return mocker.patch(
            "api.services.streaming.asyncio.sleep", new_callable=AsyncMock
        )

    async def test_stream_generator_yields_final_result_on_complete(
        self, mock_arq_redis: AsyncMock, mocker
    ):
        final_result = {"report": "done"}
        mock_job_instance = AsyncMock(
            status=AsyncMock(return_value=JobStatus.complete),
            result=AsyncMock(return_value=final_result),
        )
        mocker.patch("api.services.streaming.Job", return_value=mock_job_instance)
        results = [
            item
            async for item in create_event_generator("test_job_123", mock_arq_redis)
        ]
        assert len(results) == 1
        complete_event = results[0]
        assert complete_event["event"] == "complete"
        complete_data = json.loads(complete_event["data"])
        assert complete_data["status"] == "complete"
        assert complete_data["result"] == final_result
