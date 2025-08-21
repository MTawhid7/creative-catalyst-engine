"""
The Source Cache: Level 2 Caching Service.

This module manages the cache for processed source data from individual URLs.
It is the most critical caching layer for performance and cost-saving, as it
prevents the system from ever re-scraping or re-analyzing the same source.

It stores a JSON object for each URL containing its cleaned text and any
future structured data (like image analysis). It is designed for high-performance
batch operations.
"""

import json
from typing import Optional, Dict, List

import chromadb

from .. import settings
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- ChromaDB Client Initialization ---
_collection_name = settings.CHROMA_COLLECTION_NAME + "_sources"
_source_collection = None
try:
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    # This cache does not require embeddings, so we can use a simpler setup.
    _source_collection = chroma_client.get_or_create_collection(name=_collection_name)
    logger.info(
        f"Source Cache (L2) initialized. Collection '{_collection_name}' loaded/created."
    )
except Exception as e:
    logger.critical(
        "CRITICAL: Failed to initialize ChromaDB for Source Cache. L2 Caching will be disabled.",
        exc_info=True,
    )


def _generate_stable_id(url: str) -> str:
    """Creates a stable, hash-based ID for a given URL."""
    return str(hash(url))


# --- Public Functions ---


def check_batch(urls: List[str]) -> Dict[str, Dict]:
    """
    Checks the L2 cache for a batch of URLs and returns the data for any that are found.
    This is a high-performance, non-async function.

    Args:
        urls: A list of URL strings to check.

    Returns:
        A dictionary mapping the found URLs to their cached data (as dictionaries).
    """
    if not _source_collection or not urls:
        return {}

    logger.info(f"Checking Source Cache (L2) for {len(urls)} URLs...")

    found_sources = {}
    ids_to_check = [_generate_stable_id(url) for url in urls]

    try:
        results = _source_collection.get(
            ids=ids_to_check, include=["documents", "metadatas"]
        )

        # Defensively parse the results to prevent runtime errors
        if not results or not results.get("ids"):
            logger.info("L2 CACHE MISS: No documents found for the given batch of IDs.")
            return {}

        # Validate the structure of documents and metadatas
        documents = results.get("documents")
        metadatas = results.get("metadatas")

        if not documents or not metadatas:
            logger.info("L2 CACHE MISS: Missing documents or metadatas in results.")
            return {}

        for i, doc_id in enumerate(results["ids"]):
            # Validate that we have valid data at this index
            if (
                i >= len(documents)
                or i >= len(metadatas)
                or not documents[i]
                or not metadatas[i]
            ):
                logger.warning(f"Skipping invalid data at index {i} for ID {doc_id}")
                continue

            try:
                # Safely access metadata
                metadata = metadatas[i]
                if not isinstance(metadata, dict) or "source_url" not in metadata:
                    logger.warning(
                        f"Invalid metadata structure for ID {doc_id}. Skipping."
                    )
                    continue

                source_url = metadata["source_url"]
                cached_data = json.loads(documents[i])
                found_sources[source_url] = cached_data

            except (json.JSONDecodeError, KeyError, IndexError, TypeError) as e:
                logger.warning(
                    f"Could not parse cached data for ID {doc_id}. Skipping.",
                    exc_info=True,
                )

        logger.info(
            f"L2 CACHE HIT: Found {len(found_sources)} of {len(urls)} URLs in the cache."
        )
        return found_sources

    except Exception as e:
        logger.error(
            "An error occurred during L2 ChromaDB batch get. Assuming cache miss.",
            exc_info=True,
        )
        return {}


def add_batch(source_data: Dict[str, Dict]):
    """
    Adds a batch of newly processed source data to the L2 cache.
    This is a high-performance, non-async function.

    Args:
        source_data: A dictionary mapping URLs to their processed data.
    """
    if not _source_collection or not source_data:
        return

    logger.info(f"Adding {len(source_data)} new items to Source Cache (L2)...")

    ids = []
    documents = []
    metadatas = []

    for url, data in source_data.items():
        ids.append(_generate_stable_id(url))
        documents.append(json.dumps(data))
        metadatas.append({"source_url": url})

    try:
        _source_collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
        logger.info(f"Successfully added/updated {len(source_data)} items in L2 cache.")
    except Exception as e:
        logger.error(
            "Failed to add documents to L2 ChromaDB collection.", exc_info=True
        )
