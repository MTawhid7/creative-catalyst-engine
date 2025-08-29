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

logger = get_logger(__name__)

# This is the single point of interaction for local testing runs.
# In production, the API will provide the user_passage.
USER_PASSAGE = """
Show me a collection of dresses featuring the Bengali New Year (Pohela Boishakh). Incorporate traditional motifs, vibrant colors, and elements of Bengali culture.
"""


def cleanup_old_results():
    """Keeps the most recent N result folders and deletes the rest."""
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
    # 1. Create the RunContext to hold all data for this run
    context = RunContext(user_passage=user_passage, results_dir=settings.RESULTS_DIR)
    context.results_dir.mkdir(parents=True, exist_ok=True)
    setup_logging_run_id(context.run_id)

    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")

    # 2. Instantiate and run the orchestrator
    orchestrator = PipelineOrchestrator()
    await orchestrator.run(context)

    # 3. Finalize folder names and save artifacts
    try:
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = context.theme_slug or "untitled"
        final_folder_name = f"{timestamp_str}_{slug}"
        final_path = settings.RESULTS_DIR / final_folder_name

        # Rename the folder from its temporary UUID name
        os.rename(context.results_dir, final_path)
        context.results_dir = final_path  # Update context to point to the new path

        latest_link_path = settings.RESULTS_DIR / "latest"
        if os.path.lexists(latest_link_path):
            os.remove(latest_link_path)
        os.symlink(final_folder_name, latest_link_path)
        logger.info(f"✅ Results folder finalized as: '{final_folder_name}'")

    except Exception as e:
        logger.warning(f"⚠️ Could not perform final rename or symlink: {e}")

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
