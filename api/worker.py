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


async def _publish_status(redis_client: ArqRedis, job_id: str, context: RunContext):
    """
    A lightweight, background coroutine that periodically publishes the
    pipeline's current status to a dedicated Redis key.
    """
    status_key = f"job_progress:{job_id}"
    while not context.is_complete:
        await redis_client.set(status_key, context.current_status, ex=60)
        await asyncio.sleep(3)

    await redis_client.set(status_key, context.current_status, ex=60)


async def create_creative_report(
    ctx: dict, user_passage: str, variation_seed: int = 0
) -> Dict[str, Any]:
    """
    The main ARQ task. It now runs the core pipeline and a status publisher
    concurrently for real-time progress updates.
    """
    # --- START: DEFINITIVE RACE CONDITION FIX ---
    # The cleanup function is now called at the BEGINNING of the task.
    # This ensures that old results are deleted before the new run starts,
    # preventing the new results from being accidentally deleted.
    cleanup_old_results()
    # --- END: DEFINITIVE RACE CONDITION FIX ---

    redis_client: ArqRedis = ctx["redis"]
    job_id = ctx["job_id"]
    setup_logging_run_id(job_id)

    logger.info(
        f"Received creative brief for processing: '{user_passage[:100]}...' (Seed: {variation_seed})"
    )

    try:
        # --- CHANGE: Pass the seed to the cache check ---
        cached_result = await get_from_l0_cache(
            user_passage, variation_seed, redis_client
        )
        if cached_result:
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    # --- CHANGE: Initialize RunContext with the seed ---
    # NOTE: This requires updating the RunContext class in 'catalyst/context.py'
    context = RunContext(
        user_passage=user_passage,
        results_dir=Path("/app/results"),
        variation_seed=variation_seed,
    )

    publisher_task = asyncio.create_task(_publish_status(redis_client, job_id, context))
    pipeline_task = asyncio.create_task(run_pipeline(context))

    try:
        await pipeline_task
    finally:
        context.is_complete = True
        await publisher_task

    if not context.final_report:
        raise RuntimeError("Pipeline finished but the final report is empty.")

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=context.results_dir,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(context.results_dir),
    }

    await set_in_l0_cache(user_passage, variation_seed, final_result, redis_client)

    return final_result


def cleanup_old_results():
    """
    Keeps the most recent N result folders and deletes the rest.
    """
    from catalyst import settings

    try:
        # Get all directories, ignoring files (like .DS_Store)
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir()]
        # Sort by name, which works because the names start with a timestamp.
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)

        if len(sorted_dirs) > settings.KEEP_N_RESULTS:
            dirs_to_delete = sorted_dirs[settings.KEEP_N_RESULTS:]
            logger.info(
                f"♻️ RESULTS CLEANUP: Deleting {len(dirs_to_delete)} oldest result folders."
            )
            for old_dir in dirs_to_delete:
                shutil.rmtree(old_dir)
            logger.info("✅ Results cleanup complete.")
    except FileNotFoundError:
        logger.info("Results directory not found. Skipping cleanup.")
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
