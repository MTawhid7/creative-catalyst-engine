# api/routes/jobs.py

"""
Contains all FastAPI endpoints related to creating and monitoring creative jobs.
"""

from fastapi import APIRouter, Request, HTTPException, status as fastapi_status
from sse_starlette.sse import EventSourceResponse
from arq.connections import ArqRedis


from ..models import JobRequest, JobResponse, ImageRegenerationRequest
from ..services.streaming import create_event_generator
from catalyst.utilities.logger import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post(
    "/v1/creative-jobs",
    response_model=JobResponse,
    status_code=fastapi_status.HTTP_202_ACCEPTED,
)
async def submit_job(request: JobRequest, http_request: Request) -> JobResponse:
    redis: ArqRedis = http_request.app.state.redis
    job = await redis.enqueue_job(
        "create_creative_report", request.user_passage, request.variation_seed
    )
    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue the job.")
    return JobResponse(job_id=job.job_id, status="queued")


@router.post(
    "/v1/creative-jobs/{original_job_id}/regenerate-images",
    response_model=JobResponse,
    status_code=fastapi_status.HTTP_202_ACCEPTED,
)
async def regenerate_images(
    original_job_id: str,
    regen_request: ImageRegenerationRequest,
    http_request: Request,
) -> JobResponse:
    redis: ArqRedis = http_request.app.state.redis
    if not await redis.exists(f"job_results_path:{original_job_id}"):
        raise HTTPException(
            status_code=404,
            detail=f"No completed job found with ID '{original_job_id}'.",
        )

    # Enqueue the task with only temperature
    job = await redis.enqueue_job(
        "regenerate_images_task",
        original_job_id,
        regen_request.temperature,
    )

    if not job:
        raise HTTPException(status_code=500, detail="Failed to enqueue job.")
    logger.info(
        f"Enqueued image regeneration for job '{original_job_id}' with new job ID '{job.job_id}' and temp {regen_request.temperature}."
    )
    return JobResponse(job_id=job.job_id, status="queued")


@router.get("/v1/creative-jobs/{job_id}/stream")
async def stream_job_status(job_id: str, http_request: Request):
    """Streams the status of a creative job using Server-Sent Events (SSE)."""
    redis: ArqRedis = http_request.app.state.redis
    return EventSourceResponse(create_event_generator(job_id, redis))
