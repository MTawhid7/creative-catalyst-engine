"""
The Cache Manager: The Facade for the Multi-Layered Caching System.

This module provides a single, clean interface for the rest of the application
to interact with the various caching layers (L1 Report, L2 Source, L3 Concept).
It encapsulates the logic of which cache to call and how, simplifying the
main application workflow.
"""

import asyncio
from typing import Optional, Dict, List

from . import report_cache, source_cache, concept_cache
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)


def _create_composite_key(brief: Dict) -> str:
    """
    Creates a single, descriptive string from the enriched brief.
    This is a centralized helper to ensure the key is always generated consistently.
    """
    # Use a sorted list of keys to ensure the order is always the same,
    # and handle nested lists/dicts by converting them to a stable string format.
    key_parts = []
    for key in sorted(brief.keys()):
        value = brief.get(key)
        if isinstance(value, (list, dict)):
            key_parts.append(str(value))
        else:
            key_parts.append(str(value))
    return " | ".join(key_parts)


# --- Level 1: Report Cache Functions ---


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


# --- Level 2: Source Cache Functions ---


async def check_source_cache_async(urls: List[str]) -> Dict[str, Dict]:
    """
    Checks the L2 (Source) cache for a batch of URLs.
    Runs the synchronous check in a thread to avoid blocking the event loop.
    """
    logger.info(f"Dispatching batch check for {len(urls)} URLs to L2 Source Cache...")
    # asyncio.to_thread is the modern, correct way to run blocking code.
    return await asyncio.to_thread(source_cache.check_batch, urls)


async def add_to_source_cache_async(source_data: Dict[str, Dict]):
    """
    Adds a batch of newly scraped source data to the L2 (Source) cache.
    """
    logger.info(
        f"Dispatching batch add for {len(source_data)} items to L2 Source Cache..."
    )
    await asyncio.to_thread(source_cache.add_batch, source_data)


# --- Level 3: Concept Cache Functions ---


async def check_concept_cache_async(concept: str) -> Optional[List[str]]:
    """
    Checks the L3 (Concept) cache for research related to a specific creative concept.
    """
    logger.info(f"Dispatching check for concept '{concept}' to L3 Concept Cache...")
    return await concept_cache.check(concept)


async def add_to_concept_cache_async(concept: str, summaries: List[str]):
    """
    Adds a set of summaries to the L3 (Concept) cache for a specific creative concept.
    """
    logger.info(f"Dispatching add for concept '{concept}' to L3 Concept Cache...")
    await concept_cache.add(concept, summaries)
