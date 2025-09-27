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


# --- START: DEFINITIVE REFACTOR FOR GRANULAR STATUS ---
async def run_pipeline(context: RunContext) -> RunContext:
    """
    The core, reusable function that executes the entire creative pipeline.
    It now accepts a pre-initialized RunContext object.
    """
    # The context is now created by the worker, so we just use it.
    setup_logging_run_id(context.run_id)
    logger.info("================== RUN ID: %s ==================", context.run_id)
    logger.info("      CREATIVE CATALYST ENGINE - PROCESS STARTED         ")

    orchestrator = PipelineOrchestrator()

    try:
        is_from_cache = await orchestrator.run(context)

        # This block now only runs if the orchestrator SUCCEEDS.
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

            if not is_from_cache:
                logger.info("⚙️ Storing new artifacts in permanent L1 cache...")
                semantic_key = cache_manager._create_semantic_key(
                    context.enriched_brief
                )
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
                    logger.info(
                        f"✅ Successfully stored artifacts in L1 cache: '{doc_id}'"
                    )
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
        # The original exception must be re-raised to signal a true failure
        # to the calling worker and the test suite.
        raise

    logger.info("      CREATIVE PROCESS FINISHED for Run ID: %s", context.run_id)
    logger.info("=========================================================")
    return context


# --- END: DEFINITIVE REFACTOR FOR GRANULAR STATUS ---
