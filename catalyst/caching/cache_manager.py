# catalyst/caching/cache_manager.py

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
    # These keys are stable and represent the user's core intent.
    # We explicitly EXCLUDE non-deterministic creative fields like 'expanded_concepts'.
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
    # Iterate over our stable list of keys to ensure consistent order.
    for key in sorted(DETERMINISTIC_BRIEF_KEYS):
        value = brief.get(key)
        if value:  # Only include keys that have a value.
            # Convert lists to a stable, sorted string format.
            if isinstance(value, list):
                key_parts.append(f"{key}: {', '.join(sorted(value))}")
            else:
                key_parts.append(f"{key}: {str(value)}")

    return " | ".join(key_parts)


async def check_report_cache_async(brief: Dict) -> Optional[str]:
    """
    Checks the L0/L1 cache for a matching payload using a deterministic key.

    Args:
        brief: The enriched brief dictionary from the briefing stage.

    Returns:
        The JSON string of the cached payload if a match is found, otherwise None.
    """
    logger.info(
        "⚙️ Creating deterministic composite key and dispatching check to Report Cache..."
    )
    composite_key = _create_composite_key(brief)
    # Good practice to log the generated key for debugging consistency issues.
    logger.debug(f"⚡ Generated Cache Key: {composite_key}")
    return await report_cache.check(composite_key)


async def add_to_report_cache_async(brief: Dict, payload: Dict):
    """
    Adds a final, validated result payload to the L0/L1 cache.

    Args:
        brief: The enriched brief dictionary used to generate the key.
        payload: The full payload dictionary, including the final report and
                 the path to the cached image artifacts.
    """
    logger.info(
        "📥 Creating deterministic composite key and dispatching 'add' to Report Cache..."
    )
    composite_key = _create_composite_key(brief)
    await report_cache.add(composite_key, payload)
