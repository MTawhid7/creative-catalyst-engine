# api/worker.py

"""
This module defines the ARQ worker tasks. Each task is a standard async
function that ARQ can discover and execute.
"""

import os
import shutil
import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

from arq.connections import ArqRedis
from catalyst.utilities.logger import get_logger, setup_logging_run_id
from api.cache import get_from_l0_cache, set_in_l0_cache
from catalyst.main import run_pipeline
from catalyst.context import RunContext
from . import config as api_config
from catalyst.pipeline.processors.generation import get_image_generator
from catalyst import settings

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
    The main ARQ task. Runs the full creative pipeline.
    """
    cleanup_old_results()

    redis_client: ArqRedis = ctx["redis"]
    job_id = ctx["job_id"]
    setup_logging_run_id(job_id)

    logger.info(
        f"Received creative brief for processing: '{user_passage[:100]}...' (Seed: {variation_seed})"
    )

    try:
        cached_result = await get_from_l0_cache(
            user_passage, variation_seed, redis_client
        )
        if cached_result:
            logger.info(f"🎯 L0 Cache HIT for job '{job_id}'. Returning cached result.")
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    context = RunContext(
        user_passage=user_passage,
        results_dir=settings.RESULTS_DIR,
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

    final_results_path = context.results_dir
    await redis_client.set(f"job_results_path:{job_id}", str(final_results_path), ex=api_config.L0_CACHE_TTL_SECONDS)
    logger.info(f"Stored final results path for job '{job_id}' in Redis: {final_results_path}")

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=final_results_path,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(final_results_path),
    }

    await set_in_l0_cache(user_passage, variation_seed, final_result, redis_client)

    return final_result


async def regenerate_images_task(
    ctx: dict, original_job_id: str, temperature: float
) -> Dict[str, Any]:
    """
    A dedicated ARQ task that only regenerates images for an existing report.
    """
    redis_client: ArqRedis = ctx["redis"]
    new_job_id = ctx["job_id"]
    setup_logging_run_id(new_job_id)
    logger.info(f"Starting image regeneration for original job '{original_job_id}' with temp {temperature}.")

    original_results_path_str = await redis_client.get(f"job_results_path:{original_job_id}")
    if not original_results_path_str:
        raise FileNotFoundError(f"Could not find results path for original job ID '{original_job_id}'.")

    original_results_path = Path(original_results_path_str.decode())
    logger.info(f"Found original results at: {original_results_path}")

    context = RunContext(user_passage="Image Regeneration", results_dir=settings.RESULTS_DIR)
    context.results_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy(original_results_path / settings.TREND_REPORT_FILENAME, context.results_dir)
    shutil.copy(original_results_path / settings.PROMPTS_FILENAME, context.results_dir)

    with open(context.results_dir / settings.TREND_REPORT_FILENAME, "r") as f:
        context.final_report = json.load(f)

    image_generator = get_image_generator()
    context = await image_generator.process(context, temperature_override=temperature)

    original_timestamp = Path(original_results_path.name).name.split("_")[0]
    original_slug = "_".join(Path(original_results_path.name).name.split("_")[1:])
    temp_str = f"t{int(temperature*10)}"
    final_folder_name = f"{original_timestamp}_{original_slug}_regen_{temp_str}"
    final_path = settings.RESULTS_DIR / final_folder_name

    if final_path.exists():
        shutil.rmtree(final_path)
    shutil.move(context.results_dir, final_path)
    context.results_dir = final_path

    # --- START: THE DEFINITIVE SYMLINK FIX ---
    # After moving the folder, update the 'latest' symlink to point to it.
    latest_link_path = settings.RESULTS_DIR / "latest"
    if os.path.lexists(latest_link_path):
        os.remove(latest_link_path)
    os.symlink(final_path.name, latest_link_path, target_is_directory=True)
    logger.info(f"Symlink '/latest' updated to point to '{final_path.name}'")
    # --- END: THE DEFINITIVE SYMLINK FIX ---

    report_with_urls = _inject_public_urls(
        final_report=context.final_report,
        base_url=ASSET_BASE_URL,
        final_results_dir=context.results_dir,
    )
    final_result = {
        "final_report": report_with_urls,
        "artifacts_path": str(context.results_dir),
    }

    logger.info(f"✅ Image regeneration complete for job '{new_job_id}'.")
    return final_result


def cleanup_old_results():
    """
    Keeps the most recent N result folders and deletes the rest to save space.
    """
    try:
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir() and d.name != 'latest']
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)

        if len(sorted_dirs) > settings.KEEP_N_RESULTS:
            dirs_to_delete = sorted_dirs[settings.KEEP_N_RESULTS:]
            logger.info(f"♻️ RESULTS CLEANUP: Deleting {len(dirs_to_delete)} oldest result folders.")
            for old_dir in dirs_to_delete:
                shutil.rmtree(old_dir)
            logger.info("✅ Results cleanup complete.")
    except FileNotFoundError:
        logger.info("Results directory not found. Skipping cleanup.")
    except Exception as e:
        logger.warning(f"⚠️ Could not perform results cleanup: {e}", exc_info=True)


def _inject_public_urls(
    final_report: Dict[str, Any], base_url: str, final_results_dir: Path
) -> Dict[str, Any]:
    """
    Injects public-facing, absolute URLs into the final report for any
    generated image artifacts.
    """
    if not final_report or not final_report.get("detailed_key_pieces"):
        return final_report

    logger.info("Injecting public-facing image URLs into the final report...")
    final_folder_name = final_results_dir.name

    for piece in final_report.get("detailed_key_pieces", []):
        for path_key, url_key in [
            ("final_garment_relative_path", "final_garment_image_url"),
            ("mood_board_relative_path", "mood_board_image_url"),
        ]:
            relative_path_str = piece.get(path_key)
            if relative_path_str:
                filename = Path(relative_path_str).name
                correct_path = f"{api_config.RESULTS_MOUNT_PATH}/{final_folder_name}/{filename}"
                piece[url_key] = f"{base_url.rstrip('/')}/{correct_path}"

    logger.info("✅ Successfully injected all public image URLs.")
    return final_report