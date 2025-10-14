# catalyst/main.py

import os
import shutil
from datetime import datetime
import hashlib

from . import settings
from .context import RunContext
from .pipeline.orchestrator import PipelineOrchestrator
from .utilities.logger import get_logger, setup_logging_run_id
from .caching import cache_manager

logger = get_logger(__name__)


async def run_pipeline(context: RunContext) -> RunContext:
    """
    The core, reusable function that executes the entire creative pipeline.
    """
    setup_logging_run_id(context.run_id)
    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")

    orchestrator = PipelineOrchestrator()

    try:
        is_from_cache = await orchestrator.run(context)

        if context.final_report:
            timestamp_str = datetime.now().strftime("%Y%m%d-%H%M%S")
            slug = context.theme_slug or "untitled"
            final_folder_name = f"{timestamp_str}_{slug}"
            final_path = settings.RESULTS_DIR / final_folder_name

            if not context.results_dir.exists():
                logger.warning(
                    f"Source results directory {context.results_dir} not found. Skipping finalization."
                )
                return context

            shutil.move(context.results_dir, final_path)
            context.results_dir = final_path

            latest_link_path = settings.RESULTS_DIR / "latest"
            if os.path.lexists(latest_link_path):
                os.remove(latest_link_path)
            os.symlink(final_folder_name, latest_link_path, target_is_directory=True)
            logger.info(f"✅ Results finalized: '{final_folder_name}'")

            # --- START: THE DEFINITIVE ENCAPSULATION REFACTOR ---
            # If the result was newly generated (not from cache), add it to the
            # L1 cache. The cache_manager now handles all details of this process,
            # including copying the physical artifacts.
            if not is_from_cache:
                await cache_manager.add_to_report_cache_async(
                    brief=context.enriched_brief,
                    final_report=context.final_report,
                    variation_seed=context.variation_seed,
                    source_artifact_path=final_path,
                )
            # --- END: THE DEFINITIVE ENCAPSULATION REFACTOR ---

    except Exception as e:
        logger.critical(
            "❌ PIPELINE FAILED with an unrecoverable error.", exc_info=True
        )
        raise

    logger.info("      CREATIVE PROCESS FINISHED for Run ID: %s", context.run_id)
    logger.info("=========================================================")
    return context
