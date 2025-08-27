# api_client/exceptions.py

"""Custom exceptions for the Creative Catalyst API client."""


class APIClientError(Exception):
    """Base exception for all client-related errors."""

    pass


class ConnectionError(APIClientError):
    """Raised when the client cannot connect to the API server."""

    pass


class JobSubmissionError(APIClientError):
    """Raised when the API fails to accept a new job."""

    pass


class JobFailedError(APIClientError):
    """Raised when a Celery task fails during processing."""

    def __init__(self, job_id: str, error_message: str):
        self.job_id = job_id
        self.error_message = error_message
        super().__init__(f"Job '{job_id}' failed with error: {error_message}")


class PollingTimeoutError(APIClientError):
    """Raised when the job does not complete within the specified timeout."""

    def __init__(self, job_id: str, timeout: int):
        self.job_id = job_id
        self.timeout = timeout
        super().__init__(
            f"Polling for job '{job_id}' timed out after {timeout} seconds."
        )
