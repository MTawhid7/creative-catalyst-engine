# catalyst/main.py

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
Detail the bespoke suiting process at Kiton or Brioni, focusing on the pinnacle of artisanal craftsmanship from fabric selection to the final fitting.
"""


def cleanup_old_results():
    """Keeps the most recent N result folders and deletes the rest."""
    # This function is now only used for local testing. The worker has its own copy.
    try:
        all_dirs = [d for d in settings.RESULTS_DIR.iterdir() if d.is_dir()]
        sorted_dirs = sorted(all_dirs, key=lambda p: p.name, reverse=True)
        if len(sorted_dirs) > settings.KEEP_N_RESULTS:
            dirs_to_delete = sorted_dirs[settings.KEEP_N_RESULTS :]
            for old_dir in dirs_to_delete:
                shutil.rmtree(old_dir)
    except Exception as e:
        logger.warning(f"⚠️ Could not perform local results cleanup: {e}")


async def run_pipeline(user_passage: str) -> RunContext:
    """
    The core, reusable function that executes the entire pipeline.
    """
    context = RunContext(user_passage=user_passage, results_dir=settings.RESULTS_DIR)
    context.results_dir.mkdir(parents=True, exist_ok=True)
    setup_logging_run_id(context.run_id)
    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")

    orchestrator = PipelineOrchestrator()

    # --- START OF FIX: Restructure for transactional safety ---
    try:
        is_from_cache = await orchestrator.run(context)

        # This block now only runs if the orchestrator SUCCEEDS.
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

        # This logic is safe to run here.
        latest_link_path = settings.RESULTS_DIR / "latest"
        if os.path.lexists(latest_link_path):
            os.remove(latest_link_path)
        os.symlink(final_folder_name, latest_link_path, target_is_directory=True)
        logger.info(f"✅ Results finalized: '{final_folder_name}'")

        if not is_from_cache and context.final_report:
            logger.info("⚙️ Storing new artifacts in permanent L1 cache...")
            semantic_key = cache_manager._create_semantic_key(context.enriched_brief)
            doc_id = hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()
            artifact_dest_path = settings.ARTIFACT_CACHE_DIR / doc_id

            try:
                shutil.copytree(final_path, artifact_dest_path, dirs_exist_ok=True)
                payload_to_cache = {
                    "final_report": context.final_report,
                    "cached_results_path": doc_id,
                }
                await cache_manager.add_to_report_cache_async(
                    context.enriched_brief, payload_to_cache
                )
                logger.info(f"✅ Successfully stored artifacts in L1 cache: '{doc_id}'")
            except Exception as e:
                logger.error(
                    f"❌ Failed to add to L1 cache. Rolling back file copy.",
                    exc_info=True,
                )
                if artifact_dest_path.exists():
                    shutil.rmtree(artifact_dest_path)

    except Exception as e:
        logger.critical(
            "❌ PIPELINE FAILED with an unrecoverable error.", exc_info=True
        )
        # We still want to return the context to save debug artifacts.
    # --- END OF FIX ---

    logger.info("      CREATIVE PROCESS FINISHED for Run ID: %s", context.run_id)
    logger.info("=========================================================")
    return context


async def main():
    """Main function for local, command-line testing."""
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
