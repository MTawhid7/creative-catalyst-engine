# tests/api_client/test_client.py

import pytest
import requests_mock
import requests
from sseclient import SSEClient

from api_client.client import CreativeCatalystClient
from api_client.exceptions import (
    APIClientError,
    APIConnectionError,
    JobSubmissionError,
    JobFailedError,
)

BASE_URL = "http://test-api.com"


@pytest.fixture
def client() -> CreativeCatalystClient:
    """Provides a CreativeCatalystClient instance for testing."""
    return CreativeCatalystClient(base_url=BASE_URL)


@pytest.mark.parametrize(
    "payload",
    [
        {"user_passage": "test passage", "variation_seed": 0},
        {"user_passage": "test passage", "variation_seed": 5},
    ],
)
def test_get_creative_report_stream_happy_path(
    payload: dict, client: CreativeCatalystClient
):
    """Verify the full, successful streaming workflow with different seeds."""
    with requests_mock.Mocker() as m:
        # The mock now expects the exact payload, including the seed
        m.post(
            f"{BASE_URL}/v1/creative-jobs",
            json={"job_id": "job-123", "status": "queued"},
            additional_matcher=lambda request: request.json() == payload,
        )
        sse_payload = 'event: complete\ndata: {"status": "complete", "result": {"report": "done"}}\n\n'
        m.get(f"{BASE_URL}/v1/creative-jobs/job-123/stream", text=sse_payload)

        # Call the client with the seed
        events = list(
            client.get_creative_report_stream(
                payload["user_passage"], payload["variation_seed"]
            )
        )

        assert len(events) == 2
        assert events[1]["event"] == "complete"


def test_get_creative_report_stream_handles_connection_error(
    client: CreativeCatalystClient,
):
    """Verify that a connection error is wrapped in a custom exception."""
    with requests_mock.Mocker() as m:
        m.post(f"{BASE_URL}/v1/creative-jobs", exc=requests.exceptions.ConnectionError)
        with pytest.raises(APIConnectionError):
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
