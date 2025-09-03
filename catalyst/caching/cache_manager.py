# catalyst/caching/cache_manager.py

"""
The L1 Semantic Cache Manager.

This module provides a single, clean interface for the pipeline to interact
with the L1 semantic cache. It handles the creation of a consistent,
deterministic key from the enriched brief for vector embedding.
"""

from typing import Optional, Dict

from . import report_cache
from ..utilities.logger import get_logger

logger = get_logger(__name__)


def _create_semantic_key(brief: Dict) -> str:
    """
    Creates a single, descriptive, and stable string from the deterministic
    parts of the enriched brief. This ensures that the same core AI
    interpretation always generates the same key for semantic comparison.
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
                key_parts.append(f"{key}: {', '.join(sorted(value))}")
            else:
                key_parts.append(f"{key}: {str(value)}")
    return " | ".join(key_parts)


async def check_report_cache_async(brief: Dict) -> Optional[str]:
    """
    Checks the L1 semantic cache for a matching payload.
    """
    logger.info("⚙️ Creating deterministic key for L1 semantic cache check...")
    semantic_key = _create_semantic_key(brief)
    logger.debug(f"⚡ Generated L1 Semantic Key: {semantic_key}")
    return await report_cache.check(semantic_key)


async def add_to_report_cache_async(brief: Dict, payload: Dict):
    """
    Adds a final, validated result payload to the L1 semantic cache.
    """
    logger.info(
        "📥 Creating deterministic key and dispatching 'add' to L1 Semantic Cache..."
    )
    semantic_key = _create_semantic_key(brief)
    await report_cache.add(semantic_key, payload)
