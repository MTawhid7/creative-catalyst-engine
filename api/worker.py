# api/worker.py

import asyncio
from celery import Celery
import sys
from pathlib import Path
import os

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

    image_urls = []
    # In a real production app, this would come from a config file.
    # For now, we assume the server is running on localhost.
    # IMPORTANT: Change this if your server has a public domain name.
    base_url = "http://127.0.0.1:9500"

    results_dir = result_context.results_dir
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                # Construct the public URL path
                # results_dir.name gives the timestamped folder name
                url_path = f"/results/{results_dir.name}/{filename}"
                image_urls.append(base_url + url_path)

    return {
        "final_report": result_context.final_report,
        "artifacts_path": str(result_context.results_dir),
        "image_urls": image_urls,
    }
