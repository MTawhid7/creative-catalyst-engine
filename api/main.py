# api/main.py

import os
import json
import asyncio
from dotenv import load_dotenv
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from fastapi import FastAPI, status as fastapi_status, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Dict, Any, Optional

# Correctly import job-related classes from the 'arq.jobs' submodule.
from arq.connections import ArqRedis, create_pool
from arq.jobs import Job, JobStatus, JobDef
from sse_starlette.sse import EventSourceResponse

from .worker_settings import WorkerSettings
from catalyst.utilities.logger import get_logger

# Sentry Initialization
load_dotenv()
SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
        integrations=[FastApiIntegration()],
    )
    print("✅ Sentry configured for FastAPI.")

logger = get_logger(__name__)


# Pydantic Models
class JobRequest(BaseModel):
    user_passage: str


class JobResponse(BaseModel):
    job_id: str
    status: str


class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Lifespan Manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis: ArqRedis = await create_pool(WorkerSettings.redis_settings) # type: ignore
    logger.info("ARQ Redis connection pool created.")
    yield
    await app.state.redis.close()
    logger.info("ARQ Redis connection pool closed.")


app = FastAPI(
    title="Creative Catalyst Engine API",
    description="An API for generating fashion trend reports and images.",
    version="1.0.0",
    lifespan=lifespan,
)

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")


@app.post(
    "/v1/creative-jobs",
    response_model=JobResponse,
    status_code=fastapi_status.HTTP_202_ACCEPTED,
)
async def submit_job(request: JobRequest, http_request: Request) -> JobResponse:
    redis: ArqRedis = http_request.app.state.redis
    job = await redis.enqueue_job("create_creative_report", request.user_passage)
    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue the job.")
    return JobResponse(job_id=job.job_id, status="queued")


# --- START: DEFINITIVE API IMPLEMENTATION BASED ON VERIFIED FACTS ---
@app.get(
    "/v1/creative-jobs/{job_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(job_id: str, http_request: Request) -> JobStatusResponse:
    """
    (Fallback Polling) Retrieves job status using the verified arq API pattern.
    """
    redis: ArqRedis = http_request.app.state.redis
    job = Job(job_id, redis)

    # Use the lightweight job.status() call, which returns a clean JobStatus enum.
    current_status = await job.status()

    if current_status == JobStatus.not_found:
        raise HTTPException(
            status_code=404, detail=f"Job with ID '{job_id}' not found."
        )

    # A job's result is only available when it is complete. A failed job's result
    # is the exception it raised. We use job.result() to retrieve it.
    if current_status == JobStatus.complete:
        try:
            result = await job.result()
            # We assume a successful job returns a dictionary.
            return JobStatusResponse(job_id=job_id, status="complete", result=result)
        except Exception as e:
            # If the job failed, job.result() will re-raise the exception.
            logger.error(f"Job {job_id} failed with error: {e}", exc_info=True)
            return JobStatusResponse(job_id=job_id, status="failed", error=str(e))

    # For in-progress or queued jobs, just return the status.
    return JobStatusResponse(job_id=job_id, status=current_status.value)


@app.get("/v1/creative-jobs/{job_id}/stream")
async def stream_job_status(job_id: str, http_request: Request):
    """
    (Recommended) Streams job status using Server-Sent Events (SSE).
    """
    redis: ArqRedis = http_request.app.state.redis
    job = Job(job_id, redis)

    async def event_generator():
        initial_status = await job.status()
        if initial_status == JobStatus.not_found:
            yield {"event": "error", "data": json.dumps({"detail": "Job not found"})}
            return

        while True:
            current_status = await job.status()

            if current_status == JobStatus.complete:
                try:
                    result = await job.result()
                    result_payload = {
                        "status": "complete",
                        "result": result,
                        "error": None,
                    }
                    yield {"event": "complete", "data": json.dumps(result_payload)}
                except Exception as e:
                    # Job completed but with an error.
                    result_payload = {
                        "status": "failed",
                        "result": None,
                        "error": str(e),
                    }
                    yield {"event": "complete", "data": json.dumps(result_payload)}
                break  # Exit the loop after the final event.
            else:
                yield {
                    "event": "progress",
                    "data": json.dumps({"status": current_status.value}),
                }

            await asyncio.sleep(3)

    return EventSourceResponse(event_generator())


# --- END: DEFINITIVE API IMPLEMENTATION BASED ON VERIFIED FACTS ---
