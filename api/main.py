# api/main.py

import os
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

import arq
from arq.connections import ArqRedis, create_pool
from arq.jobs import Job, JobStatus, JobDef

from .worker_settings import WorkerSettings
from catalyst.utilities.logger import get_logger

# --- START: Sentry Initialization for FastAPI ---
# Load environment variables to ensure SENTRY_DSN is available.
load_dotenv()

SENTRY_DSN = os.getenv("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Enable performance monitoring to capture transaction data.
        traces_sample_rate=1.0,
        # Enable profiling to capture code-level performance details.
        profiles_sample_rate=1.0,
        # The FastAPIIntegration automatically hooks into the FastAPI app
        # to capture errors and performance data from web requests.
        integrations=[
            FastApiIntegration(),
        ],
    )
    print("✅ Sentry configured for FastAPI.")
# --- END: Sentry Initialization ---

logger = get_logger(__name__)


# --- Pydantic Models for Clear API Contracts ---
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


# --- Modern Lifespan Manager for Robust Connection Pooling ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the ARQ Redis connection pool during the application's lifespan.
    """
    app.state.redis = await create_pool(WorkerSettings.redis_settings)
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
    """
    Accepts a creative brief and queues it for processing with ARQ.
    """
    redis: ArqRedis = http_request.app.state.redis
    job = await redis.enqueue_job("create_creative_report", request.user_passage)

    if not job:
        logger.error("Failed to enqueue job - redis.enqueue_job returned None.")
        raise HTTPException(
            status_code=fastapi_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to enqueue the job.",
        )

    return JobResponse(job_id=job.job_id, status="queued")


@app.get(
    "/v1/creative-jobs/{job_id}",
    response_model=JobStatusResponse,
)
async def get_job_status(job_id: str, http_request: Request) -> JobStatusResponse:
    """
    Retrieves the status and result of a creative job from ARQ.
    """
    redis: ArqRedis = http_request.app.state.redis
    job = Job(job_id, redis)

    job_info: Optional[JobDef] = await job.info()

    if not job_info:
        logger.warning(f"Job not found: {job_id}")
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=f"Job with ID '{job_id}' not found.",
        )

    current_status = job_info.status  # type: ignore

    if current_status == JobStatus.complete:
        return JobStatusResponse(
            job_id=job_id, status="complete", result=job_info.result  # type: ignore
        )

    if current_status == JobStatus.failed: # type: ignore
        return JobStatusResponse(
            job_id=job_id, status="failed", error=str(job_info.result)  # type: ignore
        )

    return JobStatusResponse(job_id=job_id, status=current_status.value)
