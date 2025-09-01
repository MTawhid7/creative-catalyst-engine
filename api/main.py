# api/main.py

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from celery.result import AsyncResult
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# --- START OF FIX ---
# Import your configured Celery app instance from the worker file
from .worker import celery_app, create_creative_task

# --- END OF FIX ---

app = FastAPI(
    title="Creative Catalyst Engine API",
    description="An API for generating fashion trend reports and images.",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    task = create_creative_task.delay(request.user_passage)
    return {"job_id": task.id, "status": "queued"}


@app.get("/v1/creative-jobs/{job_id}")
def get_job_status(job_id: str):
    """
    Retrieves the status and result of a creative job.
    """
    # --- START OF FIX ---
    # Pass the app instance to AsyncResult so it knows the backend config
    task_result = AsyncResult(job_id, app=celery_app)
    # --- END OF FIX ---

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
