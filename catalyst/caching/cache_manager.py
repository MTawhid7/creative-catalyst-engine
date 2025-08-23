"""
The Cache Manager: A Simplified Facade for the L1 Report Caching System.

This module provides a single, clean interface for the application to interact
with the report cache. It handles the creation of a consistent, deterministic
cache key from the creative brief.
"""

from typing import Optional, Dict

from . import report_cache
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)


def _create_composite_key(brief: Dict) -> str:
    """
    Creates a single, descriptive, and stable string from the deterministic,
    user-facing parts of the enriched brief. This ensures that the same core
    request always generates the same cache key.
    """
    # --- START OF DEFINITIVE FIX ---
    # Define the list of keys that are stable and represent the user's core intent.
    # We explicitly EXCLUDE the non-deterministic creative fields:
    # 'expanded_concepts', 'creative_antagonist', and 'search_keywords'.
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
    # --- END OF DEFINITIVE FIX ---

    key_parts = []
    # Iterate over our stable list of keys, not the entire brief dictionary.
    for key in sorted(DETERMINISTIC_BRIEF_KEYS):
        value = brief.get(key)
        if value:  # Only include keys that have a value
            # Convert lists to a stable string format
            if isinstance(value, list):
                key_parts.append(f"{key}: {', '.join(sorted(value))}")
            else:
                key_parts.append(f"{key}: {str(value)}")

    return " | ".join(key_parts)


async def check_report_cache_async(brief: Dict) -> Optional[str]:
    """
    Checks the L1 (Report) cache for a semantically similar creative brief.
    """
    logger.info(
        "⚙️ Creating deterministic composite key and dispatching check to L1 Report Cache..."
    )
    composite_key = _create_composite_key(brief)
    logger.debug(
        f"Generated Cache Key: {composite_key}"
    )  # Add a debug log to see the key
    return await report_cache.check(composite_key)


async def add_to_report_cache_async(brief: Dict, report_data: Dict):
    """
    Adds a final, validated report to the L1 (Report) cache.
    """
    logger.info(
        "📥 Creating deterministic composite key and dispatching add to L1 Report Cache..."
    )
    composite_key = _create_composite_key(brief)
    await report_cache.add(composite_key, report_data)
