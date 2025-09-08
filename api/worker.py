# api/worker.py

import asyncio
import os
from pathlib import Path
from typing import Dict, Any

from celery import Celery
from celery.utils.log import get_task_logger

# --- START OF FIX: Remove redundant path logic ---
# This is now correctly handled by the eventlet_worker.py entry point.
# --- END OF FIX ---

logger = get_task_logger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")

celery_app = Celery(
    "creative_catalyst_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.worker"],
)


# --- START OF FIX: URL Injection Logic ---
# The function now requires the final results directory to build the correct path.
def _inject_public_urls(
    final_report: Dict[str, Any], base_url: str, final_results_dir: Path
) -> Dict[str, Any]:
    """
    Injects the full, public-facing URLs for generated images into the report.
    This uses the *final* results directory name to ensure URLs are correct
    after the directory has been renamed from its temporary run_id.
    """
    if not final_report or not final_report.get("detailed_key_pieces"):
        return final_report

    logger.info("Injecting public-facing image URLs into the final report...")
    final_folder_name = final_results_dir.name

    for piece in final_report["detailed_key_pieces"]:
        # Use the relative path only to get the filename.
        garment_path_str = piece.get("final_garment_relative_path")
        if garment_path_str:
            filename = Path(garment_path_str).name
            correct_path = f"results/{final_folder_name}/{filename}"
            piece["final_garment_image_url"] = f"{base_url.rstrip('/')}/{correct_path}"

        moodboard_path_str = piece.get("mood_board_relative_path")
        if moodboard_path_str:
            filename = Path(moodboard_path_str).name
            correct_path = f"results/{final_folder_name}/{filename}"
            piece["mood_board_image_url"] = f"{base_url.rstrip('/')}/{correct_path}"

    logger.info("✅ Successfully injected all public image URLs.")
    return final_report


# --- END OF FIX ---


@celery_app.task(name="create_creative_report")
def create_creative_report(user_passage: str) -> Dict[str, Any]:
    from api.cache import get_from_l0_cache, set_in_l0_cache
    from catalyst.main import run_pipeline
    from catalyst.context import RunContext

    logger.info(f"Received creative brief for processing: '{user_passage[:100]}...'")
    try:
        redis_client = celery_app.backend.client
        cached_result = get_from_l0_cache(user_passage, redis_client)
        if cached_result:
            return cached_result
    except Exception as e:
        logger.error(
            f"⚠️ An error occurred during L0 cache check: {e}. Proceeding with pipeline.",
            exc_info=True,
        )
    try:
        # This context object now contains the final, renamed path in context.results_dir
        context: RunContext = asyncio.run(run_pipeline(user_passage))

        if not context.final_report:
            raise RuntimeError("Pipeline finished but produced an empty final report.")

        # --- START OF FIX: Pass the final results directory to the URL injector ---
        report_with_urls = _inject_public_urls(
            final_report=context.final_report,
            base_url=ASSET_BASE_URL,
            final_results_dir=context.results_dir,  # Pass the correct, final path
        )
        # --- END OF FIX ---

        final_result = {
            "final_report": report_with_urls,
            "artifacts_path": str(context.results_dir),
        }
        if celery_app.backend.client:
            set_in_l0_cache(user_passage, final_result, celery_app.backend.client)
        return final_result
    except Exception as e:
        logger.critical(
            f"❌ A critical error occurred during the pipeline execution: {e}",
            exc_info=True,
        )
        raise
