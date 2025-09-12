# api/worker.py

"""
This module defines the ARQ worker tasks. Each task is a standard async
function that ARQ can discover and execute.
"""

import os
import shutil
from pathlib import Path
from typing import Dict, Any

# --- START: ARCHITECTURAL REFACTOR ---
# Replace Celery logger with the standard application logger.
from catalyst.utilities.logger import get_logger, setup_logging_run_id
# Import the async-native cache functions.
from api.cache import get_from_l0_cache, set_in_l0_cache
# Import the core pipeline logic.
from catalyst.main import run_pipeline
from catalyst.context import RunContext

logger = get_logger(__name__)
# --- END: ARCHITECTURAL REFACTOR ---

# These environment variables are still needed for the logic within the task.
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")


# This is a standard Python function, not tied to a specific library.
def cleanup_old_results():
    """
    Keeps the most recent N result folders and deletes the rest.
    """
    from catalyst import settings

    try:
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir()]
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)
        if len(sorted_dirs) > settings.KEEP_N_RESULTS:
            dirs_to_delete = sorted_dirs[settings.KEEP_N_RESULTS :]
            logger.info(
                f"♻️ RESULTS CLEANUP: Deleting {len(dirs_to_delete)} oldest result folders."
            )
            for old_dir in dirs_to_delete:
                shutil.rmtree(old_dir)
            logger.info("✅ Results cleanup complete.")
    except Exception as e:
        logger.warning(f"⚠️ Could not perform results cleanup: {e}")


# This is also a standard Python function.
def _inject_public_urls(
    final_report: Dict[str, Any], base_url: str, final_results_dir: Path
) -> Dict[str, Any]:
    """Injects public-facing URLs into the final report."""
    if not final_report or not final_report.get("detailed_key_pieces"):
        return final_report
    logger.info("Injecting public-facing image URLs into the final report...")
    final_folder_name = final_results_dir.name
    for piece in final_report["detailed_key_pieces"]:
        for path_key, url_key in [
            ("final_garment_relative_path", "final_garment_image_url"),
            ("mood_board_relative_path", "mood_board_image_url"),
        ]:
            relative_path_str = piece.get(path_key)
            if relative_path_str:
                filename = Path(relative_path_str).name
                correct_path = f"results/{final_folder_name}/{filename}"
                piece[url_key] = f"{base_url.rstrip('/')}/{correct_path}"
    logger.info("✅ Successfully injected all public image URLs.")
    return final_report


# --- START: DEFINITIVE ARQ TASK IMPLEMENTATION ---
async def create_creative_report(ctx: dict, user_passage: str) -> Dict[str, Any]:
    """
    This is the main ARQ task. It's a regular async function that receives
    a context dictionary (`ctx`) and the job arguments.
    """
    # ARQ provides the Redis client and other job info in the context dict.
    redis_client = ctx['redis']
    job_id = ctx['job_id']

    # Associate the run_id with the job_id for consistent logging.
    setup_logging_run_id(job_id)

    logger.info(f"Received creative brief for processing: '{user_passage[:100]}...'")

    try:
        # Await the async cache check function.
        cached_result = await get_from_l0_cache(user_passage, redis_client)
        if cached_result:
            cleanup_old_results()
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    # No more manual loop management. We can now directly await the pipeline.
    # This is the core of the stability fix.
    context: RunContext = await run_pipeline(user_passage)

    # The orchestrator will raise an error if the report is empty, which ARQ
    # will correctly catch and report as a job failure.

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=context.results_dir,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(context.results_dir),
    }

    # Await the async cache set function.
    await set_in_l0_cache(user_passage, final_result, redis_client)

    cleanup_old_results()

    return final_result
# --- END: DEFINITIVE ARQ TASK IMPLEMENTATION ---