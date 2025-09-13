# api_client/client.py

import os
import requests
import json
from sseclient import SSEClient
from .exceptions import (
    ConnectionError,
    JobSubmissionError,
    JobFailedError,
)

# Best Practice: Use an environment variable for the API URL, with a sensible default.
API_BASE_URL = os.getenv("CREATIVE_CATALYST_API_URL", "http://127.0.0.1:9500")


class CreativeCatalystClient:
    """A client for interacting with the Creative Catalyst Engine API."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.submit_url = f"{self.base_url}/v1/creative-jobs"

    def _get_stream_url(self, job_id: str) -> str:
        """Constructs the URL for the job status stream."""
        return f"{self.submit_url}/{job_id}/stream"

    def _submit_job(self, passage: str) -> str:
        """Helper function to submit the job and return the job ID."""
        print(f"Submitting job to {self.submit_url}...")
        payload = {"user_passage": passage}
        response = requests.post(self.submit_url, json=payload, timeout=15)
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("job_id")
        if not job_id:
            raise JobSubmissionError("API did not return a job_id.")
        return job_id

    def get_creative_report(self, passage: str) -> dict:
        """
        Submits a creative brief and waits for the final report by listening
        to a real-time Server-Sent Events (SSE) stream.
        """
        try:
            # 1. Submit the Job to get a job ID.
            job_id = self._submit_job(passage)
            print(f"✅ Successfully submitted job with ID: {job_id}")

            # 2. Connect to the SSE streaming endpoint.
            stream_url = self._get_stream_url(job_id)
            print(f"📡 Connecting to event stream at {stream_url}...")

            response = requests.get(stream_url, stream=True, timeout=360)
            response.raise_for_status()

            # --- START: DEFINITIVE, ROBUST, AND TYPE-SAFE FIX ---
            # The requests library's iter_content() returns a generator of bytes,
            # which is exactly what SSEClient expects. We use # type: ignore to
            # suppress a known, pedantic "false positive" from the linter caused
            # by imprecise type hints in the 'requests' library.
            client = SSEClient(response.iter_content())  # type: ignore
            # --- END: DEFINITIVE, ROBUST, AND TYPE-SAFE FIX ---

            for event in client.events():
                if event.event == "progress":
                    data = json.loads(event.data)
                    print(f"   Progress: Job status is now '{data['status']}'...")

                elif event.event == "complete":
                    data = json.loads(event.data)
                    if data.get("status") == "complete":
                        print("✅ Job complete. Returning result.")
                        return data.get("result", {})
                    else:
                        raise JobFailedError(job_id, data.get("error", "Unknown error"))

                elif event.event == "error":
                    data = json.loads(event.data)
                    raise JobSubmissionError(
                        data.get("detail", "Stream failed with an error event")
                    )

            raise JobSubmissionError(
                "Stream ended unexpectedly without a 'complete' or 'error' event."
            )

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Could not connect to the API at {self.base_url}. Is the server running?"
            ) from e
        except requests.exceptions.HTTPError as e:
            raise JobSubmissionError(
                f"API returned an HTTP error: {e.response.status_code} {e.response.text}"
            ) from e
        except requests.exceptions.ReadTimeout:
            raise ConnectionError(
                "Connection to the event stream timed out. The job may still be running on the server."
            )
