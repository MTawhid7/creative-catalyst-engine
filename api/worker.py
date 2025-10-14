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
from catalyst import settings  # <-- IMPORT SETTINGS

logger = get_logger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")


async def _publish_status(redis_client: ArqRedis, job_id: str, context: RunContext):
    # ... (function is unchanged) ...
    status_key = f"job_progress:{job_id}"
    while not context.is_complete:
        await redis_client.set(status_key, context.current_status, ex=60)
        await asyncio.sleep(3)
    await redis_client.set(status_key, context.current_status, ex=60)


async def create_creative_report(
    ctx: dict, user_passage: str, variation_seed: int = 0
) -> Dict[str, Any]:
    # ... (function logic is unchanged) ...
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
            return cached_result
    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)

    # --- START: REMOVE HARDCODED PATH ---
    context = RunContext(
        user_passage=user_passage,
        results_dir=settings.RESULTS_DIR,  # Use the path from settings
        variation_seed=variation_seed,
    )
    # --- END: REMOVE HARDCODED PATH ---

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
    await redis_client.set(
        f"job_results_path:{job_id}",
        str(final_results_path),
        ex=api_config.L0_CACHE_TTL_SECONDS,
    )
    logger.info(
        f"Stored final results path for job '{job_id}' in Redis: {final_results_path}"
    )

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
    ctx: dict, original_job_id: str, seed: int, temperature: Optional[float]
) -> Dict[str, Any]:
    # ... (function logic is unchanged) ...
    redis_client: ArqRedis = ctx["redis"]
    new_job_id = ctx["job_id"]
    setup_logging_run_id(new_job_id)
    logger.info(
        f"Starting image regeneration for original job '{original_job_id}' with seed {seed} and temp {temperature or 'default'}."
    )
    original_results_path_str = await redis_client.get(
        f"job_results_path:{original_job_id}"
    )
    if not original_results_path_str:
        raise FileNotFoundError(
            f"Could not find results path for original job ID '{original_job_id}'."
        )
    original_results_path = Path(original_results_path_str.decode())
    logger.info(f"Found original results at: {original_results_path}")

    # --- START: REMOVE HARDCODED PATH ---
    context = RunContext(
        user_passage="Image Regeneration", results_dir=settings.RESULTS_DIR
    )  # Use the path from settings
    # --- END: REMOVE HARDCODED PATH ---

    context.results_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(
        original_results_path / settings.TREND_REPORT_FILENAME,
        context.results_dir / settings.TREND_REPORT_FILENAME,
    )
    shutil.copy(
        original_results_path / settings.PROMPTS_FILENAME,
        context.results_dir / settings.PROMPTS_FILENAME,
    )
    with open(context.results_dir / settings.TREND_REPORT_FILENAME, "r") as f:
        context.final_report = json.load(f)
    image_generator = get_image_generator()
    context = await image_generator.process(
        context, seed_override=seed, temperature_override=temperature
    )

    original_slug = "_".join(Path(original_results_path.name).name.split("_")[1:])
    temp_str = f"t{int(temperature*10)}" if temperature is not None else "tdef"
    final_folder_name = f"{Path(original_results_path.name).name.split('_')[0]}_{original_slug}_regen_s{seed}_{temp_str}"
    final_path = settings.RESULTS_DIR / final_folder_name
    shutil.move(context.results_dir, final_path)
    context.results_dir = final_path

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


# ... (cleanup_old_results and _inject_public_urls are unchanged) ...
def cleanup_old_results():
    # ...
    pass


def _inject_public_urls(
    final_report: Dict[str, Any], base_url: str, final_results_dir: Path
) -> Dict[str, Any]:
    # ...
    return final_report
