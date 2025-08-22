"""
The Cache Manager: A Simplified Facade for the L1 Report Caching System.

This module provides a single, clean interface for the application to interact
with the report cache. It handles the creation of a consistent cache key from
the creative brief.
"""

from typing import Optional, Dict

from . import report_cache
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)


def _create_composite_key(brief: Dict) -> str:
    """
    Creates a single, descriptive, and stable string from the enriched brief.
    This is a centralized helper to ensure the key is always generated consistently.
    Sorting the keys guarantees that the same brief will always produce the same key.
    """
    key_parts = []
    for key in sorted(brief.keys()):
        value = brief.get(key)
        # Convert lists and dicts to a stable string format
        if isinstance(value, (list, dict)):
            key_parts.append(str(value))
        else:
            key_parts.append(str(value))
    return " | ".join(key_parts)


async def check_report_cache_async(brief: Dict) -> Optional[str]:
    """
    Checks the L1 (Report) cache for a semantically similar creative brief.
    """
    logger.info("Dispatching check to L1 Report Cache...")
    composite_key = _create_composite_key(brief)
    return await report_cache.check(composite_key)


async def add_to_report_cache_async(brief: Dict, report_data: Dict):
    """
    Adds a final, validated report to the L1 (Report) cache.
    """
    logger.info("Dispatching add to L1 Report Cache...")
    composite_key = _create_composite_key(brief)
    await report_cache.add(composite_key, report_data)
