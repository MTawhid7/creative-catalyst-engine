# tests/api_client/test_client.py

import pytest
import json
import requests

# Import the class we are testing
from api_client.client import CreativeCatalystClient

# --- START: CLEANUP ---
# This is a cleaner way to import. No redundant alias.
from api_client.exceptions import (
    APIConnectionError,
    JobSubmissionError,
    JobFailedError,
)

# Define the path to the requests library used by the client
REQUESTS_PATH = "api_client.client.requests"


def test_get_creative_report_stream_happy_path(mocker):
    """
    Tests the full, successful lifecycle of a job from the client's perspective:
    1. Job is submitted successfully.
    2. A progress event is received.
    3. The final 'complete' event with the report is received.
    """
    # ARRANGE
    # 1. Mock the entire 'requests' library.
    mock_requests = mocker.patch(REQUESTS_PATH)

    # 2. Configure the mock for the initial POST request to submit the job.
    mock_post_response = mocker.MagicMock()
    mock_post_response.raise_for_status.return_value = None
    mock_post_response.json.return_value = {"job_id": "test-job-123"}
    mock_requests.post.return_value = mock_post_response

    # 3. Configure the mock for the subsequent GET request to the SSE stream.
    # We need to simulate the raw byte content that the sseclient library expects.
    progress_event_data = {"status": "Phase 3: Synthesis"}
    complete_event_data = {"status": "complete", "result": {"final_report": "done"}}

    # Format the data into valid SSE message strings.
    sse_stream_content = [
        f"event: progress\ndata: {json.dumps(progress_event_data)}\n\n".encode("utf-8"),
        f"event: complete\ndata: {json.dumps(complete_event_data)}\n\n".encode("utf-8"),
    ]

    mock_get_response = mocker.MagicMock()
    mock_get_response.raise_for_status.return_value = None
    # The iter_content method must return an iterator.
    mock_get_response.iter_content.return_value = iter(sse_stream_content)
    mock_requests.get.return_value = mock_get_response

    # ACT
    # Instantiate the client and run the generator, collecting all yielded results into a list.
    client = CreativeCatalystClient()
    results = list(client.get_creative_report_stream("A test prompt"))

    # ASSERT
    # 1. Verify that the POST request was made correctly.
    mock_requests.post.assert_called_once_with(
        "http://127.0.0.1:9500/v1/creative-jobs",
        json={"user_passage": "A test prompt"},
        timeout=15,
    )

    # 2. Verify that the GET request for the stream was made correctly.
    mock_requests.get.assert_called_once_with(
        "http://127.0.0.1:9500/v1/creative-jobs/test-job-123/stream",
        stream=True,
        timeout=360,
    )

    # 3. Verify the sequence and content of the yielded events.
    assert len(results) == 3
    assert results[0] == {"event": "job_submitted", "job_id": "test-job-123"}
    assert results[1] == {"event": "progress", "status": "Phase 3: Synthesis"}
    assert results[2] == {"event": "complete", "result": {"final_report": "done"}}


def test_client_handles_connection_error(mocker):
    """
    Tests that the client raises a custom ConnectionError if it cannot
    connect to the server.
    """
    # ARRANGE
    mock_requests = mocker.patch(REQUESTS_PATH)
    # Simulate a network failure during the POST request.
    mock_requests.post.side_effect = requests.exceptions.ConnectionError("Network down")

    # ACT & ASSERT
    client = CreativeCatalystClient()
    # Use pytest.raises to assert that the correct exception is thrown.
    with pytest.raises(APIConnectionError, match="Could not connect to the API"):
        # We still need to consume the generator to trigger the code.
        list(client.get_creative_report_stream("A test prompt"))


def test_client_handles_http_error_on_submit(mocker):
    """
    Tests that the client raises a JobSubmissionError if the server returns
    an HTTP error during job submission.
    """
    # ARRANGE
    mock_requests = mocker.patch(REQUESTS_PATH)
    mock_post_response = mocker.MagicMock()
    # Simulate a 500 Internal Server Error.
    http_error = requests.exceptions.HTTPError("Server Error")
    http_error.response = mocker.MagicMock(status_code=500)
    mock_post_response.raise_for_status.side_effect = http_error
    mock_requests.post.return_value = mock_post_response

    # ACT & ASSERT
    client = CreativeCatalystClient()
    with pytest.raises(JobSubmissionError, match="API returned an HTTP error: 500"):
        list(client.get_creative_report_stream("A test prompt"))


def test_client_handles_job_failed_event(mocker):
    """
    Tests that the client raises a JobFailedError if the SSE stream reports
    that the job itself has failed on the worker.
    """
    # ARRANGE
    mock_requests = mocker.patch(REQUESTS_PATH)

    # Simulate a successful POST
    mock_post_response = mocker.MagicMock()
    mock_post_response.raise_for_status.return_value = None
    mock_post_response.json.return_value = {"job_id": "failed-job-123"}
    mock_requests.post.return_value = mock_post_response

    # Simulate an SSE stream that sends a 'failed' event
    failed_event_data = {"status": "failed", "error": "Pipeline crashed unexpectedly."}
    sse_stream_content = [
        f"event: complete\ndata: {json.dumps(failed_event_data)}\n\n".encode("utf-8"),
    ]

    mock_get_response = mocker.MagicMock()
    mock_get_response.raise_for_status.return_value = None
    mock_get_response.iter_content.return_value = iter(sse_stream_content)
    mock_requests.get.return_value = mock_get_response

    # ACT & ASSERT
    client = CreativeCatalystClient()
    with pytest.raises(
        JobFailedError, match="failed with error: Pipeline crashed unexpectedly"
    ):
        list(client.get_creative_report_stream("A test prompt"))
