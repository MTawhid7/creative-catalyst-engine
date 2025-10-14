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
    """
    Submits a new, lightweight job to regenerate only the images for a
    previously completed creative report, using a new seed and optional temperature.
    """
    redis: ArqRedis = http_request.app.state.redis
    if not await redis.exists(f"job_results_path:{original_job_id}"):
        raise HTTPException(
            status_code=fastapi_status.HTTP_404_NOT_FOUND,
            detail=f"No completed job found with ID '{original_job_id}'. Cannot regenerate images.",
        )

    # Enqueue the new task with both seed and temperature
    job = await redis.enqueue_job(
        "regenerate_images_task",
        original_job_id,
        regen_request.seed,
        regen_request.temperature,
    )

    if not job:
        raise HTTPException(
            status_code=500, detail="Failed to enqueue the image regeneration job."
        )
    logger.info(
        f"Enqueued image regeneration for job '{original_job_id}' with new job ID '{job.job_id}', seed {regen_request.seed}, and temperature {regen_request.temperature or 'default'}."
    )
    return JobResponse(job_id=job.job_id, status="queued")


@router.get("/v1/creative-jobs/{job_id}/stream")
async def stream_job_status(job_id: str, http_request: Request):
    """Streams the status of a creative job using Server-Sent Events (SSE)."""
    redis: ArqRedis = http_request.app.state.redis
    return EventSourceResponse(create_event_generator(job_id, redis))
