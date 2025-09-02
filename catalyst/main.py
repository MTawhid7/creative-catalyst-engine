# catalyst/main.py

"""
The Main Entry Point for the Creative Catalyst Engine.

This file can be run directly for local testing. For production use, the
`run_pipeline` function is imported and executed by a background worker.
"""

import asyncio
import time
import os
import shutil
from pathlib import Path
from datetime import datetime

from . import settings
from .context import RunContext
from .pipeline.orchestrator import PipelineOrchestrator
from .utilities.logger import get_logger, setup_logging_run_id
from .caching import cache_manager

logger = get_logger(__name__)

USER_PASSAGE = """
How has Brunello Cucinelli elevated the basic T-shirt and polo shirt through the use of noble fibers and a philosophy of 'quiet luxury'?
"""


def cleanup_old_results():
    """
    Keeps the most recent N result folders in the user-facing `results` directory
    and deletes the rest. This function does NOT touch the permanent artifact cache.
    """
    try:
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir()]
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)

        if len(sorted_dirs) > settings.KEEP_N_RESULTS:
            dirs_to_delete = sorted_dirs[settings.KEEP_N_RESULTS :]
            logger.info(
                f"♻️ RESULTS CLEANUP: Found {len(sorted_dirs)} result folders. Deleting {len(dirs_to_delete)} oldest ones."
            )
            for old_dir in dirs_to_delete:
                shutil.rmtree(old_dir)
                logger.debug(f"🗑️ Deleted old result folder: {old_dir.name}")
            logger.info("✅ Results cleanup complete.")

    except Exception as e:
        logger.warning(f"⚠️ Could not perform results cleanup: {e}")


async def run_pipeline(user_passage: str) -> RunContext:
    """
    The core, reusable function that executes the entire pipeline for a given
    user passage and returns the final context object.
    """
    context = RunContext(user_passage=user_passage, results_dir=settings.RESULTS_DIR)
    context.results_dir.mkdir(parents=True, exist_ok=True)
    setup_logging_run_id(context.run_id)

    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")

    orchestrator = PipelineOrchestrator()
    is_from_cache = await orchestrator.run(context)

    final_folder_name = ""
    try:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = context.theme_slug or "untitled"
        final_folder_name = f"{timestamp_str}_{slug}"
        final_path = settings.RESULTS_DIR / final_folder_name

        os.rename(context.results_dir, final_path)
        context.results_dir = final_path

        latest_link_path = settings.RESULTS_DIR / "latest"
        if os.path.lexists(latest_link_path):
            os.remove(latest_link_path)
        os.symlink(final_folder_name, latest_link_path)
        logger.info(
            f"✅ User-facing results folder finalized as: '{final_folder_name}'"
        )

    except Exception as e:
        logger.warning(f"⚠️ Could not perform final rename or symlink: {e}")

    # --- START OF CACHE FIX ---
    # If the run was new, copy the final artifacts to the permanent cache location.
    if not is_from_cache and context.final_report and final_path.exists():
        logger.info("⚙️ Caching: Storing new artifacts in permanent cache...")

        # Use the deterministic hash as the permanent folder name.
        brief_key = cache_manager._create_composite_key(context.enriched_brief)
        doc_id_str = str(hash(brief_key))
        artifact_dest_path = settings.ARTIFACT_CACHE_DIR / doc_id_str

        try:
            # Copy the entire finalized results folder to the permanent cache.
            shutil.copytree(final_path, artifact_dest_path, dirs_exist_ok=True)

            # The payload now points to the stable, permanent folder name (the hash).
            payload_to_cache = {
                "final_report": context.final_report,
                "cached_results_path": doc_id_str,
            }
            await cache_manager.add_to_report_cache_async(
                context.enriched_brief, payload_to_cache
            )
            logger.info(
                f"✅ Successfully stored artifacts in cache at '{artifact_dest_path}'"
            )
        except Exception as e:
            logger.error(
                f"❌ Failed to copy artifacts to permanent cache: {e}", exc_info=True
            )
    # --- END OF CACHE FIX ---

    logger.info("      CREATIVE PROCESS FINISHED for Run ID: %s", context.run_id)
    logger.info("=========================================================")

    return context


async def main():
    """The main asynchronous function for local, command-line testing."""
    start_time = time.time()
    await run_pipeline(USER_PASSAGE)
    duration = time.time() - start_time
    logger.info("Local run finished in %.2f seconds", duration)
    cleanup_old_results()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Process interrupted by user.")
    except Exception as e:
        logger.critical(
            "❌ A top-level, unhandled exception occurred: %s", e, exc_info=True
        )
