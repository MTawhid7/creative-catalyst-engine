# catalyst/caching/cache_manager.py

"""
The L1 Semantic Cache Manager.
"""

import shutil
import hashlib
from pathlib import Path
from typing import Optional, Dict

from . import report_cache
from ..utilities.logger import get_logger
from .. import settings

logger = get_logger(__name__)


def _create_semantic_key(brief: Dict, variation_seed: int) -> str:
    """
    Creates a single, descriptive, and stable string from the deterministic
    parts of the enriched brief and the variation seed.
    """
    DETERMINISTIC_BRIEF_KEYS = [
        "theme_hint",
        "garment_type",
        "brand_category",
        "target_audience",
        "region",
        "key_attributes",
        "season",
        "year",
    ]
    key_parts = []
    for key in sorted(DETERMINISTIC_BRIEF_KEYS):
        value = brief.get(key)
        if value:
            if isinstance(value, list):
                key_parts.append(f"{key}: {', '.join(sorted(map(str, value)))}")
            else:
                key_parts.append(f"{key}: {str(value)}")

    # --- ADD: Append the variation seed to the key parts ---
    key_parts.append(f"variation_seed: {variation_seed}")

    return " | ".join(key_parts)


# --- CHANGE: Update the function to accept and pass the variation_seed ---
async def check_report_cache_async(brief: Dict, variation_seed: int) -> Optional[str]:
    """
    Checks the L1 semantic cache for a matching payload.
    """
    logger.info("⚙️ Creating deterministic key for L1 semantic cache check...")
    semantic_key = _create_semantic_key(brief, variation_seed)
    logger.debug(f"⚡ Generated L1 Semantic Key: {semantic_key}")
    return await report_cache.check(semantic_key)


# --- START: THE DEFINITIVE ENCAPSULATION REFACTOR ---
async def add_to_report_cache_async(
    brief: Dict,
    final_report: Dict,
    variation_seed: int,
    source_artifact_path: Path,
):
    """
    Adds a final result to the L1 cache. This is a two-part process:
    1. Copies the physical artifacts (images, reports) to a permanent, hashed
       directory in the artifact cache.
    2. Adds a reference to that directory in the L1 semantic (vector) cache.
    """
    logger.info("⚙️ Storing new artifacts in permanent L1 cache...")
    semantic_key = _create_semantic_key(brief, variation_seed)
    doc_id = hashlib.sha256(semantic_key.encode("utf-8")).hexdigest()
    artifact_dest_path = settings.ARTIFACT_CACHE_DIR / doc_id

    try:
        # Step 1: Copy physical artifacts
        shutil.copytree(source_artifact_path, artifact_dest_path, dirs_exist_ok=True)

        # Step 2: Create payload and add to semantic cache
        payload_to_cache = {
            "final_report": final_report,
            "cached_results_path": doc_id,
        }
        await report_cache.add(semantic_key, payload_to_cache)
        logger.info(f"✅ Successfully stored artifacts in L1 cache: '{doc_id}'")

    except Exception as e:
        logger.error(
            f"❌ Failed to add to L1 cache. Rolling back file copy.",
            exc_info=True,
        )
        # Rollback: If caching fails, remove the copied artifacts to avoid orphans.
        if artifact_dest_path.exists():
            shutil.rmtree(artifact_dest_path)


# --- END: THE DEFINITIVE ENCAPSULATION REFACTOR ---
