# api/main.py

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from celery.result import AsyncResult
from fastapi.staticfiles import StaticFiles

# --- START OF FIX: Import Path to construct absolute paths ---
from pathlib import Path

# --- END OF FIX ---

from .worker import celery_app

app = FastAPI(
    title="Creative Catalyst Engine API",
    description="An API for generating fashion trend reports and images.",
    version="1.0.0",
)


class JobRequest(BaseModel):
    user_passage: str


class JobResponse(BaseModel):
    job_id: str
    status: str


# --- START OF FIX: Use an absolute path for the StaticFiles mount ---
# This makes the server independent of the directory it's run from.
# It builds the path to the 'results' directory from the location of this file.
RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"

# This allows the API to serve the generated images directly.
app.mount("/results", StaticFiles(directory=RESULTS_DIR), name="results")
# --- END OF FIX ---


@app.post(
    "/v1/creative-jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_job(request: JobRequest):
    """
    Accepts a creative brief, queues it for processing, and returns a job ID.
    """
    task = celery_app.send_task("create_creative_report", args=[request.user_passage])
    return {"job_id": task.id, "status": "queued"}


@app.get("/v1/creative-jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieves the status and result of a creative job.
    """
    task_result = AsyncResult(job_id, app=celery_app)

    if task_result.failed():
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "job_id": job_id,
                "status": "failed",
                "error": str(task_result.result),
            },
        )

    if task_result.ready():
        return {"job_id": job_id, "status": "complete", "result": task_result.get()}
    else:
        return {"job_id": job_id, "status": "processing", "result": None}
