"""
The Main Entry Point for the Creative Catalyst Engine.

This file initializes the pipeline, creates the RunContext, and starts the
orchestrator to execute the end-to-end workflow.
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

# This is the single point of interaction for the user.
USER_PASSAGE = """
Show Hermès bespoke coats paired with bohemian layering styles.
"""

def cleanup_old_results():
    """Keeps the most recent N result folders and deletes the rest."""
    try:
        # Get all items in the results directory that are directories
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir()]

        # Sort directories by name (since they start with a sortable timestamp)
        # This is more reliable than modification time.
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)

        # Check if cleanup is needed
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


async def main():
    """The main asynchronous function that sets up and runs the pipeline."""

    # 1. Create the RunContext to hold all data for this run
    context = RunContext(user_passage=USER_PASSAGE, results_dir=settings.RESULTS_DIR)

    # Create the initial temporary directory before anything else
    context.results_dir.mkdir(parents=True, exist_ok=True)

    # 2. Setup the logging context
    setup_logging_run_id(context.run_id)

    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")
    logger.info("=========================================================")

    # 3. Instantiate the orchestrator.
    orchestrator = PipelineOrchestrator()

    # 4. Run the orchestrator's main process
    start_time = time.time()
    await orchestrator.run(context)
    duration = time.time() - start_time

    # 5. Rename folder, create symlink, and cleanup
    final_folder_name = ""
    try:
        # Create the final, elegant folder name
        timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
        slug = context.theme_slug or "untitled"
        final_folder_name = f"{timestamp_str}_{slug}"

        final_path = settings.RESULTS_DIR / final_folder_name

        # Rename the folder from its temporary UUID name to the final, elegant name
        os.rename(context.results_dir, final_path)
        logger.info(f"✅ Results folder renamed to: '{final_folder_name}'")

        # Create/Update the 'latest' symlink to point to the new name
        latest_link_path = settings.RESULTS_DIR / "latest"
        if os.path.lexists(latest_link_path):
            os.remove(latest_link_path)

        # Symlink target must be a string, not a Path object on some systems
        os.symlink(final_folder_name, latest_link_path)
        logger.info(f"✅ Symlink created: 'latest' -> '{final_folder_name}'")

    except Exception as e:
        logger.warning(f"⚠️ Could not perform final rename or symlink: {e}")

    logger.info("=========================================================")
    logger.info("      CREATIVE PROCESS FINISHED in %.2f seconds", duration)
    logger.info("================== END RUN ID: %s ==================", context.run_id)

    # 6. Run the cleanup process at the very end
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
