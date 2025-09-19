# tests/api/test_main.py

import pytest
from unittest.mock import MagicMock, AsyncMock

from fastapi.testclient import TestClient
from arq.jobs import Job, JobStatus

# Import the FastAPI app object from your main application file
from api.main import app

# Define the path to the function we need to mock to isolate the test
ARQ_CREATE_POOL_PATH = "api.main.create_pool"


@pytest.fixture
def mock_redis():
    """A fixture to provide a mock ArqRedis client."""
    return AsyncMock()


# --- START: THE DEFINITIVE FIX ---
@pytest.fixture
def client(mocker, mock_redis: AsyncMock):
    """
    This fixture provides a FastAPI TestClient with a correctly managed lifespan,
    ensuring the app.state.redis is properly mocked.
    """
    # 1. Mock the create_pool function to return our mock_redis instance.
    mocker.patch(ARQ_CREATE_POOL_PATH, return_value=mock_redis)

    # 2. Use a 'with' statement to manually manage the app's lifespan.
    # This ensures that the startup event (which creates app.state.redis)
    # runs AFTER our mock is in place.
    with TestClient(app) as test_client:
        yield test_client
    # The 'with' block also handles the shutdown event automatically.


# --- END: THE DEFINITIVE FIX ---


def test_submit_job_success(client: TestClient, mock_redis: AsyncMock):
    """
    Tests the happy path for job submission.
    """
    # ARRANGE
    mock_redis.enqueue_job.return_value = AsyncMock(job_id="test_job_123")

    # ACT
    response = client.post("/v1/creative-jobs", json={"user_passage": "A test prompt"})

    # ASSERT
    assert response.status_code == 202
    assert response.json()["job_id"] == "test_job_123"
    mock_redis.enqueue_job.assert_called_once_with(
        "create_creative_report", "A test prompt"
    )


def test_submit_job_failure(client: TestClient, mock_redis: AsyncMock):
    """
    Tests the failure path for job submission when enqueueing fails.
    """
    # ARRANGE
    mock_redis.enqueue_job.return_value = None

    # ACT
    response = client.post(
        "/v1/creative-jobs", json={"user_passage": "A failing prompt"}
    )

    # ASSERT
    assert response.status_code == 500
    assert "Failed to enqueue the job" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_job_status_complete(client: TestClient, mocker):
    """
    Tests the job status endpoint for a completed job.
    """
    # ARRANGE
    mock_job_instance = MagicMock()
    mock_job_instance.status = AsyncMock(return_value=JobStatus.complete)
    mock_job_instance.result = AsyncMock(return_value={"report": "done"})
    mocker.patch("api.main.Job", return_value=mock_job_instance)

    # ACT
    response = client.get("/v1/creative-jobs/some_job_id")

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["result"] == {"report": "done"}


@pytest.mark.asyncio
async def test_get_job_status_in_progress(client: TestClient, mocker):
    """
    Tests the job status endpoint for a job that is still running.
    """
    # ARRANGE
    mock_job_instance = MagicMock()
    mock_job_instance.status = AsyncMock(return_value=JobStatus.in_progress)
    mocker.patch("api.main.Job", return_value=mock_job_instance)

    # ACT
    response = client.get("/v1/creative-jobs/some_job_id")

    # ASSERT
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"
    assert response.json()["result"] is None


@pytest.mark.asyncio
async def test_get_job_status_not_found(client: TestClient, mocker):
    """
    Tests the job status endpoint for a job ID that does not exist.
    """
    # ARRANGE
    mock_job_instance = MagicMock()
    mock_job_instance.status = AsyncMock(return_value=JobStatus.not_found)
    mocker.patch("api.main.Job", return_value=mock_job_instance)

    # ACT
    response = client.get("/v1/creative-jobs/non_existent_id")

    # ASSERT
    assert response.status_code == 404
    assert "not found" in response.json()["detail"]
