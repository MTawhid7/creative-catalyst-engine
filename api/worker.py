# api/worker.py

import asyncio
import os
import re
from pathlib import Path
from typing import Dict, Any

from celery import Celery
from celery.utils.log import get_task_logger

# --- START OF IMPROVEMENT: CLEAN IMPORTS ---
# Import the new, self-contained L0 cache helper functions.
from .cache import get_from_l0_cache, set_in_l0_cache

# --- END OF IMPROVEMENT ---

# Import the core pipeline function and context object
from catalyst.main import run_pipeline
from catalyst.context import RunContext

# --- Configuration ---
logger = get_task_logger(__name__)
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
ASSET_BASE_URL = os.getenv("ASSET_BASE_URL", "http://127.0.0.1:9500")

# Initialize the Celery application
celery_app = Celery(
    "creative_catalyst_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["api.worker"],
)

# --- Helper Functions for Result Formatting ---


def _create_slug(text: str) -> str:
    """
    Creates a URL-friendly slug from a string. This must be consistent
    with how image filenames are generated.
    """
    if not text:
        return "untitled"
    text = text.replace("'", "").replace("&", "and")
    text = re.sub(r"[^a-zA-Z0-9\s-]", "", text.lower())
    slug = re.sub(r"[\s-]+", "-", text).strip("-")
    return slug


def _inject_image_urls_into_report(
    final_report: Dict[str, Any], results_dir: Path, base_url: str
) -> Dict[str, Any]:
    """
    Scans the results directory for generated images and injects their
    public URLs directly into the corresponding 'detailed_key_pieces' entries.
    """
    logger.info("Injecting public image URLs into the final report...")
    try:
        public_path = f"results/{results_dir.name}"
        url_map = {}
        if results_dir.exists():
            for file_path in results_dir.glob("*.png"):
                url_map[file_path.stem] = (
                    f"{base_url.rstrip('/')}/{public_path}/{file_path.name}"
                )

        if not url_map:
            logger.warning(
                "No .png images found in results directory. URLs will not be injected."
            )
            return final_report

        if (
            "detailed_key_pieces" in final_report
            and final_report["detailed_key_pieces"]
        ):
            for piece in final_report["detailed_key_pieces"]:
                piece_name = piece.get("key_piece_name")
                if not piece_name:
                    continue

                piece_slug = _create_slug(piece_name)
                garment_slug = piece_slug
                moodboard_slug = f"{piece_slug}-moodboard"

                piece["final_garment_image_url"] = url_map.get(garment_slug)
                piece["mood_board_image_url"] = url_map.get(moodboard_slug)

        logger.info("✅ Successfully injected image URLs.")
        return final_report

    except Exception as e:
        logger.error(f"❌ Failed to inject image URLs into report: {e}", exc_info=True)
        return final_report


@celery_app.task(name="create_creative_report")
def create_creative_report(user_passage: str) -> Dict[str, Any]:
    """
    The main Celery task that executes the full creative pipeline, with a
    pre-inference L0 cache for user intent.
    """
    logger.info(f"Received creative brief for processing: '{user_passage[:100]}...'")

    redis_client = None
    try:
        # Get a direct, synchronous connection to the Redis client from Celery's backend
        redis_client = celery_app.backend.client

        # --- START OF IMPROVEMENT: SIMPLIFIED L0 CACHE LOGIC ---
        # Call the self-contained, synchronous cache helper function.
        cached_result = get_from_l0_cache(user_passage, redis_client)
        if cached_result:
            # If the cache hits, we are done. Return the result immediately.
            return cached_result
        # --- END OF IMPROVEMENT ---

    except Exception as e:
        # A failure in the cache check should not fail the job.
        logger.error(
            f"⚠️ An error occurred during L0 cache check: {e}. Proceeding with pipeline.",
            exc_info=True,
        )

    try:
        # L0 CACHE MISS: Run the entire pipeline. This is the expensive part.
        context: RunContext = asyncio.run(run_pipeline(user_passage))

        final_report = context.final_report
        if not final_report:
            raise RuntimeError("Pipeline finished but produced an empty final report.")

        # Format the successful result by injecting the public image URLs.
        modified_report = _inject_image_urls_into_report(
            final_report=final_report,
            results_dir=context.results_dir,
            base_url=ASSET_BASE_URL,
        )

        final_result = {
            "final_report": modified_report,
            "artifacts_path": str(context.results_dir),
        }

        # --- START OF IMPROVEMENT: SIMPLIFIED L0 CACHE LOGIC ---
        # If the pipeline was successful, store the new result in the L0 cache.
        if redis_client:
            # Call the self-contained, synchronous cache helper function.
            set_in_l0_cache(user_passage, final_result, redis_client)
        # --- END OF IMPROVEMENT ---

        return final_result

    except Exception as e:
        logger.critical(
            f"❌ A critical error occurred during the pipeline execution: {e}",
            exc_info=True,
        )
        # Propagate the exception to mark the Celery task as FAILED.
        raise
