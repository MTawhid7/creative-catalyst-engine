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
from typing import Generator, Dict, Any, Union

# Best Practice: Use an environment variable for the API URL, with a sensible default.
API_BASE_URL = os.getenv("CREATIVE_CATALYST_API_URL", "http://127.0.0.1:9500")


# --- START: DEFINITIVE GENERATOR-BASED REFACTOR ---
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

    def get_creative_report_stream(
        self, passage: str
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Submits a creative brief and YIELDS real-time status updates.
        The final yielded object will contain the full report.
        """
        try:
            # 1. Submit the Job to get a job ID.
            job_id = self._submit_job(passage)
            yield {"event": "job_submitted", "job_id": job_id}

            # 2. Connect to the SSE streaming endpoint.
            stream_url = self._get_stream_url(job_id)
            print(f"📡 Connecting to event stream at {stream_url}...")

            response = requests.get(stream_url, stream=True, timeout=360)
            response.raise_for_status()

            client = SSEClient(response.iter_content())  # type: ignore

            for event in client.events():
                data = json.loads(event.data)

                if event.event == "progress":
                    # Yield a progress update.
                    yield {"event": "progress", "status": data.get("status")}

                elif event.event == "complete":
                    # The final message was received; the job is done.
                    if data.get("status") == "complete":
                        # Yield the final, complete report and stop.
                        yield {"event": "complete", "result": data.get("result", {})}
                        return
                    else:
                        # The job finished with a 'failed' status.
                        raise JobFailedError(job_id, data.get("error", "Unknown error"))

                elif event.event == "error":
                    # The server sent an explicit error event (e.g., job not found).
                    raise JobSubmissionError(
                        data.get("detail", "Stream failed with an error event")
                    )

            raise JobSubmissionError(
                "Stream ended unexpectedly without a 'complete' event."
            )

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Could not connect to the API: {e}") from e
        except requests.exceptions.HTTPError as e:
            raise JobSubmissionError(
                f"API returned an HTTP error: {e.response.status_code}"
            ) from e
        except requests.exceptions.ReadTimeout:
            raise ConnectionError("Connection to the event stream timed out.")


# --- END: DEFINITIVE GENERATOR-BASED REFACTOR ---
