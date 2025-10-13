# catalyst/caching/cache_manager.py

"""
The L1 Semantic Cache Manager.
"""

from typing import Optional, Dict

from . import report_cache
from ..utilities.logger import get_logger

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


# --- CHANGE: Update the function to accept and pass the variation_seed ---
async def add_to_report_cache_async(brief: Dict, payload: Dict, variation_seed: int):
    """
    Adds a final, validated result payload to the L1 semantic cache.
    """
    logger.info(
        "📥 Creating deterministic key and dispatching 'add' to L1 Semantic Cache..."
    )
    semantic_key = _create_semantic_key(brief, variation_seed)
    await report_cache.add(semantic_key, payload)
