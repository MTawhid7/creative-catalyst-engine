# api/worker.py

import asyncio
from celery import Celery
import sys
from pathlib import Path

# We keep the global scope clean. No application imports here.

celery_app = Celery(
    "creative_catalyst_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)


@celery_app.task(name="create_creative_task")
def create_creative_task(user_passage: str) -> dict:
    """
    The background task that runs the entire Creative Catalyst Engine pipeline.
    """
    # --- START OF FINAL FIX: PATH CORRECTION AND LAZY IMPORT ---
    # This is the most robust way to ensure the worker process can find our code.
    # We add the project's root directory to the Python path *inside the task*.
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Now that the path is corrected, we can safely import our application.
    from catalyst.main import run_pipeline

    # --- END OF FINAL FIX ---

    result_context = asyncio.run(run_pipeline(user_passage))

    return {
        "final_report": result_context.final_report,
        "artifacts_path": str(result_context.results_dir),
    }
