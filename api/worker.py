# api/worker.py

import asyncio
from celery import Celery
import sys
from pathlib import Path
import os
import logging  # <--- ADD THIS IMPORT

# We keep the global scope clean. No application imports here.

celery_app = Celery(
    "creative_catalyst_worker",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
)

# --- START OF MODIFICATION: ADD A LOGGER ---
# Get a logger instance to see detailed output in your Celery terminal
log = logging.getLogger(__name__)
# --- END OF MODIFICATION ---


@celery_app.task(name="create_creative_task")
def create_creative_task(user_passage: str) -> dict:
    """
    The background task that runs the entire Creative Catalyst Engine pipeline.
    """
    project_root = Path(__file__).resolve().parent.parent
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    from catalyst.main import run_pipeline

    result_context = asyncio.run(run_pipeline(user_passage))

    image_urls = []
    # Use the correct IP address for your Mac on the network
    base_url = "http://192.168.10.189:9500"

    results_dir = result_context.results_dir

    # --- START OF MODIFICATION: ROBUST FILE FINDING & LOGGING ---
    log.info(f"--- Starting image URL generation ---")
    log.info(f"Checking for images in directory: {results_dir}")

    if os.path.exists(results_dir):
        log.info(f"Directory exists. Listing contents...")
        try:
            # Log the complete list of files found for debugging
            all_files = os.listdir(results_dir)
            log.info(f"Files found: {all_files}")

            # Now, loop through the found files
            for filename in all_files:
                if filename.lower().endswith((".png", ".jpg", ".jpeg")):
                    log.info(f"Found image file: {filename}. Constructing URL.")
                    # The folder name is the last part of the path
                    folder_name = os.path.basename(results_dir)
                    url_path = f"/results/{folder_name}/{filename}"
                    image_urls.append(base_url + url_path)

            if not image_urls:
                log.warning(
                    "Directory was checked, but no files with image extensions (.png, .jpg) were found."
                )

        except Exception as e:
            log.error(
                f"An error occurred while listing directory contents: {e}",
                exc_info=True,
            )
    else:
        log.error(
            f"CRITICAL: The results directory '{results_dir}' does not exist. Cannot find images."
        )

    log.info(f"--- Finished image URL generation. Found {len(image_urls)} URLs. ---")
    # --- END OF MODIFICATION ---

    return {
        "final_report": result_context.final_report,
        "artifacts_path": str(result_context.results_dir),
        "image_urls": image_urls,
    }
