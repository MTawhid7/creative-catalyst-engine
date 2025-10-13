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

    # --- START: MODIFICATION ---
    # We use pytest.mark.parametrize to test two scenarios:
    # 1. The user doesn't provide a seed (it should default to 0).
    # 2. The user provides a specific seed (e.g., 5).
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
        """Verify the job is enqueued with the correct passage and seed."""
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_job = MagicMock(job_id="test_job_123")
        mock_arq_redis.enqueue_job.return_value = mock_job

        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json=payload)

            # Assert the API response is correct
            assert response.status_code == 202
            assert response.json()["job_id"] == "test_job_123"

            # Assert that arq.enqueue_job was called with the correct arguments
            mock_arq_redis.enqueue_job.assert_awaited_once_with(
                "create_creative_report", payload["user_passage"], expected_seed
            )

    # --- END: MODIFICATION ---

    def test_submit_job_failure(self, mock_arq_redis: AsyncMock, mocker):
        mocker.patch("api.main.create_pool", return_value=mock_arq_redis)
        mock_arq_redis.enqueue_job.return_value = None

        with TestClient(app) as client:
            response = client.post("/v1/creative-jobs", json={"user_passage": "test"})
            assert response.status_code == 500


@pytest.mark.asyncio
class TestEventGeneratorLogic:
    """Tests the core async generator logic directly."""

    # This test class remains unchanged as the streaming logic was not modified.

    @pytest.fixture(autouse=True)
    def mock_sleep(self, mocker):
        return mocker.patch(
            "api.services.streaming.asyncio.sleep", new_callable=AsyncMock
        )

    async def test_stream_generator_yields_final_result_on_complete(
        self, mock_arq_redis: AsyncMock, mocker
    ):
        final_result = {"report": "done"}
        mock_job_instance = AsyncMock()
        mock_job_instance.status.return_value = JobStatus.complete
        mock_job_instance.result.return_value = final_result
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

    async def test_stream_generator_job_not_found(
        self, mock_arq_redis: AsyncMock, mocker
    ):
        mock_job_instance = AsyncMock(
            status=AsyncMock(return_value=JobStatus.not_found)
        )
        mocker.patch("api.services.streaming.Job", return_value=mock_job_instance)
        results = [
            item async for item in create_event_generator("not_found", mock_arq_redis)
        ]
        assert len(results) == 1
        assert results[0]["event"] == "error"
