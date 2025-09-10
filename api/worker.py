# api/worker.py

import asyncio
import os
import shutil
from pathlib import Path
from typing import Dict, Any

from celery import Celery
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")

celery_app = Celery(
    "creative_catalyst_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.worker"],
)


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


# --- START OF DEFINITIVE FIX ---
# Revert the task signature to a standard synchronous function.
@celery_app.task(name="create_creative_report")
def create_creative_report(user_passage: str) -> Dict[str, Any]:
    # --- END OF DEFINITIVE FIX ---
    from api.cache import get_from_l0_cache, set_in_l0_cache
    from catalyst.main import run_pipeline
    from catalyst.context import RunContext

    logger.info(f"Received creative brief for processing: '{user_passage[:100]}...'")
    try:
        redis_client = celery_app.backend.client
        cached_result = get_from_l0_cache(user_passage, redis_client)
        if cached_result:
            cleanup_old_results()
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    # --- START OF DEFINITIVE FIX: The robust asyncio execution pattern ---
    # This pattern creates a new, clean event loop for each task, runs the
    # async pipeline, and then properly closes the loop. This fully isolates
    # asyncio from eventlet and prevents all loop-related conflicts.
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        context: RunContext = loop.run_until_complete(run_pipeline(user_passage))
    finally:
        loop.close()
    # --- END OF DEFINITIVE FIX ---

    if not context.final_report:
        raise RuntimeError("Pipeline finished but produced an empty final report.")

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=context.results_dir,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(context.results_dir),
    }

    if celery_app.backend.client:
        set_in_l0_cache(user_passage, final_result, celery_app.backend.client)

    cleanup_old_results()

    return final_result
