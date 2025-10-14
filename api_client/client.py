# api_client/client.py

import os
import requests
import json
from sseclient import SSEClient

from requests.exceptions import (
    ConnectionError as RequestsConnectionError,
    HTTPError,
    ReadTimeout,
)
from .exceptions import (
    APIConnectionError,
    JobSubmissionError,
    JobFailedError,
)

from typing import Generator, Dict, Any, Optional

API_BASE_URL = os.getenv("CREATIVE_CATALYST_API_URL", "http://127.0.0.1:9500")


class CreativeCatalystClient:
    """A client for interacting with the Creative Catalyst Engine API."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.submit_url = f"{self.base_url}/v1/creative-jobs"

    def _get_stream_url(self, job_id: str) -> str:
        return f"{self.submit_url}/{job_id}/stream"

    # --- START: REFACTOR FOR REGENERATION ---
    def _stream_job_events(self, job_id: str) -> Generator[Dict[str, Any], None, None]:
        """Private helper to handle the SSE streaming logic for any job ID."""
        stream_url = self._get_stream_url(job_id)
        print(f"📡 Connecting to event stream at {stream_url}...")
        response = requests.get(stream_url, stream=True, timeout=360)
        response.raise_for_status()
        client = SSEClient((chunk for chunk in response.iter_content()))
        for event in client.events():
            data = json.loads(event.data)
            if event.event == "progress":
                yield {"event": "progress", "status": data.get("status")}
            elif event.event == "complete":
                if data.get("status") == "complete":
                    yield {"event": "complete", "result": data.get("result", {})}
                    return
                else:
                    raise JobFailedError(job_id, data.get("error", "Unknown error"))
            elif event.event == "error":
                raise JobSubmissionError(
                    data.get("detail", "Stream failed with an error event")
                )
        raise JobSubmissionError(
            "Stream ended unexpectedly without a 'complete' event."
        )

    # --- END: REFACTOR FOR REGENERATION ---

    def _submit_job(self, passage: str, variation_seed: int) -> str:
        """Helper function to submit the job and return the job ID."""
        print(f"Submitting job to {self.submit_url} with seed {variation_seed}...")
        payload = {"user_passage": passage, "variation_seed": variation_seed}
        response = requests.post(self.submit_url, json=payload, timeout=15)
        response.raise_for_status()
        job_data = response.json()
        job_id = job_data.get("job_id")
        if not job_id:
            raise JobSubmissionError("API did not return a job_id.")
        return job_id

    def get_creative_report_stream(
        self, passage: str, variation_seed: int = 0
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Submits a new creative brief and YIELDS real-time status updates.
        """
        try:
            job_id = self._submit_job(passage, variation_seed)
            yield {"event": "job_submitted", "job_id": job_id}

            # Use the refactored streaming helper
            yield from self._stream_job_events(job_id)

        except RequestsConnectionError as e:
            raise APIConnectionError(f"Could not connect to the API: {e}") from e
        except HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            raise JobSubmissionError(
                f"API returned an HTTP error: {status_code}"
            ) from e
        except ReadTimeout as e:
            raise APIConnectionError("Connection to the event stream timed out.") from e

    # --- START: NEW METHOD FOR IMAGE REGENERATION ---
    def regenerate_images_stream(
        self,
        original_job_id: str,
        seed: int,
        temperature: Optional[float] = None,
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Submits a job to regenerate ONLY the images for a previous report
        and YIELDS real-time status updates for the new job.
        """
        try:
            regen_url = f"{self.submit_url}/{original_job_id}/regenerate-images"
            print(
                f"Submitting image regeneration request to {regen_url} with seed {seed}..."
            )
            payload: Dict[str, Any] = {"seed": seed}
            if temperature is not None:
                payload["temperature"] = temperature

            response = requests.post(regen_url, json=payload, timeout=15)
            response.raise_for_status()
            job_data = response.json()
            new_job_id = job_data.get("job_id")
            if not new_job_id:
                raise JobSubmissionError(
                    "API did not return a new job_id for regeneration."
                )

            yield {"event": "job_submitted", "job_id": new_job_id}

            # Use the same refactored streaming helper for the new job
            yield from self._stream_job_events(new_job_id)

        except RequestsConnectionError as e:
            raise APIConnectionError(f"Could not connect to the API: {e}") from e
        except HTTPError as e:
            status_code = e.response.status_code if e.response else "unknown"
            # Provide a more specific error message for 404
            if e.response and e.response.status_code == 404:
                raise JobSubmissionError(
                    f"API returned 404 Not Found. Is the original job ID '{original_job_id}' correct and has it completed successfully?"
                ) from e
            raise JobSubmissionError(
                f"API returned an HTTP error: {status_code}"
            ) from e
        except ReadTimeout as e:
            raise APIConnectionError("Connection to the event stream timed out.") from e

    # --- END: NEW METHOD FOR IMAGE REGENERATION ---
