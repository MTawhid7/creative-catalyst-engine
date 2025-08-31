# api_client/client.py

import requests
import time
from .exceptions import (
    ConnectionError,
    JobSubmissionError,
    JobFailedError,
    PollingTimeoutError,
)


class CreativeCatalystClient:
    """
    A client for interacting with the Creative Catalyst Engine API.

    This client abstracts the asynchronous, polling-based nature of the API
    into a single, synchronous method call.
    """

    def __init__(self, base_url: str = "http://127.0.0.1:9500"):
        self.base_url = base_url.rstrip("/")
        self.submit_url = f"{self.base_url}/v1/creative-jobs"

    def _get_status_url(self, job_id: str) -> str:
        return f"{self.submit_url}/{job_id}"

    def get_creative_report(
        self, passage: str, poll_interval: int = 5, timeout: int = 300
    ) -> dict:
        """
        Submits a creative brief and waits for the final report.

        Args:
            passage: The creative brief to submit.
            poll_interval: Seconds to wait between status checks.
            timeout: Maximum seconds to wait for the job to complete.

        Returns:
            A dictionary containing the final fashion trend report.

        Raises:
            ConnectionError: If unable to connect to the API server.
            JobSubmissionError: If the API rejects the job submission.
            JobFailedError: If the background job fails during execution.
            PollingTimeoutError: If the job does not complete in time.
        """
        try:
            # 1. Submit the Job
            payload = {"user_passage": passage}
            response = requests.post(self.submit_url, json=payload)
            response.raise_for_status()  # Raises HTTPError for 4xx/5xx responses

            job_data = response.json()
            job_id = job_data.get("job_id")
            if not job_id:
                raise JobSubmissionError("API did not return a job_id.")

            print(f"Successfully submitted job with ID: {job_id}")

            # 2. Poll for the Result
            start_time = time.time()
            while time.time() - start_time < timeout:
                print(f"Polling status for job {job_id}...")
                status_response = requests.get(self._get_status_url(job_id))
                status_response.raise_for_status()

                status_data = status_response.json()
                job_status = status_data.get("status")

                if job_status == "complete":
                    print("Job complete. Returning result.")
                    return status_data.get("result", {})

                if job_status == "failed":
                    error_msg = status_data.get("error", "Unknown error")
                    raise JobFailedError(job_id, error_msg)

                # Wait before the next poll
                time.sleep(poll_interval)

            # 3. Handle Timeout
            raise PollingTimeoutError(job_id, timeout)

        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(
                f"Could not connect to the API at {self.base_url}. Is the server running?"
            ) from e
        except requests.exceptions.HTTPError as e:
            raise JobSubmissionError(
                f"API returned an error: {e.response.status_code} {e.response.text}"
            ) from e
