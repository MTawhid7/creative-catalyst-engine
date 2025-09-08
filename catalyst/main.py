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
import hashlib

from . import settings
from .context import RunContext
from .pipeline.orchestrator import PipelineOrchestrator
from .utilities.logger import get_logger, setup_logging_run_id
from .caching import cache_manager

logger = get_logger(__name__)

USER_PASSAGE = """
How did Moncler successfully merge high-performance technology with high-fashion aesthetics in its iconic puffer jackets, influencing the rise of luxury streetwear?
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

    try:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = context.theme_slug or "untitled"
        final_folder_name = f"{timestamp_str}_{slug}"
        final_path = settings.RESULTS_DIR / final_folder_name

        if not context.results_dir.exists():
            logger.warning(
                f"Source results directory {context.results_dir} not found. Skipping finalization."
            )
            return context

        os.rename(context.results_dir, final_path)
        context.results_dir = final_path

        latest_link_path = settings.RESULTS_DIR / "latest"
        if os.path.lexists(latest_link_path):
            os.remove(latest_link_path)
        os.symlink(final_folder_name, latest_link_path)
        logger.info(
            f"✅ User-facing results folder finalized as: '{final_folder_name}'"
        )

        if not is_from_cache and context.final_report:
            logger.info("⚙️ Caching: Storing new artifacts in permanent L1 cache...")

            # --- START OF FIX: Implement transactional safety for L1 cache population ---
            semantic_key = cache_manager._create_semantic_key(context.enriched_brief)
            doc_id = hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()
            artifact_dest_path = settings.ARTIFACT_CACHE_DIR / doc_id

            try:
                # Step 1: Copy files to their permanent destination.
                shutil.copytree(final_path, artifact_dest_path, dirs_exist_ok=True)

                # Step 2: Attempt to add the entry to the database.
                payload_to_cache = {
                    "final_report": context.final_report,
                    "cached_results_path": doc_id,
                }
                await cache_manager.add_to_report_cache_async(
                    context.enriched_brief, payload_to_cache
                )
                logger.info(
                    f"✅ Successfully stored artifacts in L1 cache at '{artifact_dest_path}'"
                )

            except Exception as e:
                # Step 3 (Rollback): If the DB write fails, delete the copied files.
                logger.error(
                    f"❌ Failed to add entry to L1 vector cache: {e}. Rolling back file copy.",
                    exc_info=True,
                )
                if artifact_dest_path.exists():
                    logger.warning(
                        f"🗑️ Rolling back: Deleting orphaned artifacts from {artifact_dest_path}"
                    )
                    shutil.rmtree(artifact_dest_path)
            # --- END OF FIX ---

    except Exception as e:
        logger.warning(
            f"⚠️ Could not perform final rename or symlink: {e}", exc_info=True
        )

    logger.info("      CREATIVE PROCESS FINISHED for Run ID: %s", context.run_id)
    logger.info("=========================================================")

    return context


async def main():
    """
    The main asynchronous function for local, command-line testing.
    """
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
            "A top-level, unhandled exception occurred: %s", e, exc_info=True
        )
