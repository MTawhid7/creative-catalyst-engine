# tests/api_client/test_client.py

import pytest
import requests_mock
import requests  # <-- START: THE DEFINITIVE FIX: Import the real requests library
from sseclient import SSEClient

from api_client.client import CreativeCatalystClient
from api_client.exceptions import (
    APIClientError,
    APIConnectionError,
    JobSubmissionError,
    JobFailedError,
)

BASE_URL = "http://test-api.com"


# --- Unit Test for Exceptions ---
def test_exception_hierarchy():
    """Verify that custom exceptions inherit from the base error."""
    assert issubclass(APIConnectionError, APIClientError)
    assert issubclass(JobSubmissionError, APIClientError)
    assert issubclass(JobFailedError, APIClientError)


# --- Integration Tests for the Client ---


@pytest.fixture
def client() -> CreativeCatalystClient:
    """Provides a CreativeCatalystClient instance for testing."""
    return CreativeCatalystClient(base_url=BASE_URL)


def test_get_creative_report_stream_happy_path(client: CreativeCatalystClient):
    """
    Verify the full, successful streaming workflow from submission to completion.
    """
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE_URL}/v1/creative-jobs",
            json={"job_id": "job-123", "status": "queued"},
        )
        sse_payload = (
            'event: progress\ndata: {"status": "Phase 3: Research & Synthesis"}\n\n'
            'event: complete\ndata: {"status": "complete", "result": {"report": "done"}, "error": null}\n\n'
        )
        m.get(f"{BASE_URL}/v1/creative-jobs/job-123/stream", text=sse_payload)

        events = list(client.get_creative_report_stream("test passage"))

        assert len(events) == 3
        assert events[2]["event"] == "complete"


def test_get_creative_report_stream_handles_connection_error(
    client: CreativeCatalystClient,
):
    """Verify that a connection error is wrapped in a custom exception."""
    with requests_mock.Mocker() as m:
        # --- START: THE DEFINITIVE FIX ---
        # Use the real exception from the requests library to simulate the error.
        m.post(f"{BASE_URL}/v1/creative-jobs", exc=requests.exceptions.ConnectionError)
        # --- END: THE DEFINITIVE FIX ---

        with pytest.raises(APIConnectionError):
            list(client.get_creative_report_stream("test"))


def test_get_creative_report_stream_handles_http_error(client: CreativeCatalystClient):
    """Verify that a 500 server error is wrapped in a custom exception."""
    with requests_mock.Mocker() as m:
        m.post(
            f"{BASE_URL}/v1/creative-jobs",
            status_code=500,
            reason="Internal Server Error",
        )
        with pytest.raises(JobSubmissionError):
            list(client.get_creative_report_stream("test"))


def test_get_creative_report_stream_handles_job_failure_event(
    client: CreativeCatalystClient,
):
    """Verify that a 'failed' status in the complete event raises JobFailedError."""
    with requests_mock.Mocker() as m:
        m.post(f"{BASE_URL}/v1/creative-jobs", json={"job_id": "job-123"})
        sse_payload = 'event: complete\ndata: {"status": "failed", "result": null, "error": "Pipeline crashed"}\n\n'
        m.get(f"{BASE_URL}/v1/creative-jobs/job-123/stream", text=sse_payload)
        with pytest.raises(JobFailedError, match="Pipeline crashed"):
            list(client.get_creative_report_stream("test"))


def test_get_creative_report_stream_handles_unexpected_disconnect(
    client: CreativeCatalystClient,
):
    """Verify that a stream ending without a 'complete' event raises an error."""
    with requests_mock.Mocker() as m:
        m.post(f"{BASE_URL}/v1/creative-jobs", json={"job_id": "job-123"})
        sse_payload = 'event: progress\ndata: {"status": "Starting..."}\n\n'
        m.get(f"{BASE_URL}/v1/creative-jobs/job-123/stream", text=sse_payload)
        with pytest.raises(JobSubmissionError, match="Stream ended unexpectedly"):
            list(client.get_creative_report_stream("test"))
