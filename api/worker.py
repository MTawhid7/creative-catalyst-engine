# api/worker.py

"""
This module defines the ARQ worker tasks. Each task is a standard async
function that ARQ can discover and execute.

This version is enhanced to publish granular, real-time status updates
to a Redis channel during pipeline execution.
"""

import os
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any

from arq.connections import ArqRedis
from catalyst.utilities.logger import get_logger, setup_logging_run_id
from api.cache import get_from_l0_cache, set_in_l0_cache
from catalyst.main import run_pipeline
from catalyst.context import RunContext

logger = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")


# --- START: GRANULAR STATUS PUBLISHING REFACTOR ---
async def _publish_status(redis_client: ArqRedis, job_id: str, context: RunContext):
    """
    A lightweight, background coroutine that periodically publishes the
    pipeline's current status to a dedicated Redis key.
    """
    status_key = f"job_progress:{job_id}"
    while not context.is_complete:
        # Set the current status with a 60-second expiry. If the worker
        # crashes hard, the key will eventually disappear.
        await redis_client.set(status_key, context.current_status, ex=60)
        await asyncio.sleep(3)  # Publish status once per second.

    # One final update to ensure the "Finishing..." status is captured.
    await redis_client.set(status_key, context.current_status, ex=60)


async def create_creative_report(ctx: dict, user_passage: str) -> Dict[str, Any]:
    """
    The main ARQ task. It now runs the core pipeline and a status publisher
    concurrently for real-time progress updates.
    """
    redis_client: ArqRedis = ctx["redis"]
    job_id = ctx["job_id"]
    setup_logging_run_id(job_id)

    logger.info(f"Received creative brief for processing: '{user_passage[:100]}...'")

    try:
        cached_result = await get_from_l0_cache(user_passage, redis_client)
        if cached_result:
            cleanup_old_results()
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    # We now create the context here so we can pass it to both concurrent tasks.
    # The results_dir path must be the path *inside* the container.
    context = RunContext(user_passage=user_passage, results_dir=Path("/app/results"))

    # Create the two concurrent tasks.
    publisher_task = asyncio.create_task(_publish_status(redis_client, job_id, context))
    pipeline_task = asyncio.create_task(run_pipeline(context))

    try:
        # Wait for the main pipeline task to complete.
        await pipeline_task
    finally:
        # This block ensures that the publisher is always stopped gracefully,
        # whether the pipeline succeeds or fails.
        context.is_complete = True
        await publisher_task

    # The orchestrator will raise an error if the report is empty.

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=context.results_dir,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(context.results_dir),
    }

    await set_in_l0_cache(user_passage, final_result, redis_client)
    cleanup_old_results()
    return final_result


# --- END: GRANULAR STATUS PUBLISHING REFACTOR ---


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
