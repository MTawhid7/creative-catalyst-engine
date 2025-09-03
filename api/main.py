# api/main.py

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from celery.result import AsyncResult
from fastapi.staticfiles import StaticFiles

# --- START OF FIX ---
# We no longer need to import the function itself, only the celery_app instance.
from .worker import celery_app

# --- END OF FIX ---

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


class ResultResponse(BaseModel):
    job_id: str
    status: str
    result: dict | None = None


# This allows the API to serve the generated images directly.
app.mount("/results", StaticFiles(directory="results"), name="results")


@app.post(
    "/v1/creative-jobs",
    response_model=JobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def submit_job(request: JobRequest):
    """
    Accepts a creative brief, queues it for processing, and returns a job ID.
    """
    # --- START OF FIX ---
    # Call the task by its registered name string using `send_task`.
    # This is the most robust and type-safe method.
    # The first argument is the task name, and the `args` argument is a
    # list of positional arguments for the task function.
    task = celery_app.send_task("create_creative_report", args=[request.user_passage])
    # --- END OF FIX ---
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
                "error": str(task_result.result),  # Get the exception message
            },
        )

    if task_result.ready():
        return {"job_id": job_id, "status": "complete", "result": task_result.get()}
    else:
        return {"job_id": job_id, "status": "processing", "result": None}
