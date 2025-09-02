# catalyst/caching/report_cache.py

"""
The Report Cache: A Two-Level Caching Service.

This module manages the cache for complete, final report payloads, which include
both the structured report data and the path to the generated image artifacts.

It implements a two-level lookup strategy for optimal performance:
- L0 (Exact Match): A fast, hash-based lookup for identical creative briefs.
- L1 (Semantic Match): A vector-based search for semantically similar briefs,
  acting as a fallback if the L0 cache misses.
"""

import json
from typing import Optional, Dict

import chromadb

from .. import settings
from ..clients import gemini_client
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- ChromaDB Client Initialization ---
_collection_name = settings.CHROMA_COLLECTION_NAME
_report_collection = None
try:
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    _report_collection = chroma_client.get_or_create_collection(name=_collection_name)
    logger.info(
        f"✅ Report Cache (L0/L1) initialized. Collection '{_collection_name}' loaded/created."
    )
except Exception as e:
    logger.critical(
        "❌ CRITICAL: Failed to initialize ChromaDB for Report Cache. Caching will be disabled.",
        exc_info=True,
    )


async def check(brief_key: str) -> Optional[str]:
    """
    Checks the cache for a matching report payload using a two-level strategy.

    Args:
        brief_key: The deterministic, composite key generated from the user's brief.

    Returns:
        The JSON string of the entire cached payload if a match is found,
        otherwise None.
    """
    if not _report_collection:
        logger.warning("⚠️ Report collection is not available. Skipping cache check.")
        return None

    doc_id = str(hash(brief_key))

    # --- L0 Cache Check (Exact Match) ---
    try:
        logger.info(f"⚙️ Checking L0 Cache (Exact Match) with ID: {doc_id}...")
        results = _report_collection.get(ids=[doc_id])
        if results and results.get("documents") and results["documents"]:
            logger.warning(
                f"🎯 L0 CACHE HIT! (Exact Match) Found payload with ID: {doc_id}"
            )
            return results["documents"][0]
    except Exception as e:
        logger.error(
            "❌ An error occurred during L0 ChromaDB get. Proceeding to L1.",
            exc_info=True,
        )

    # --- L1 Cache Check (Semantic Match) ---
    logger.info("💨 L0 MISS. Checking L1 Cache (Semantic Match)...")
    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error("❌ Could not generate embedding for L1 cache check. Skipping.")
        return None

    try:
        results = _report_collection.query(query_embeddings=[embedding], n_results=1)

        if (
            not results
            or not results.get("ids")
            or not results["ids"]
            or not results["ids"][0]
            or not results.get("documents")
            or not results["documents"]
            or not results["documents"][0]
            or not results.get("distances")
            or not results["distances"]
            or not results["distances"][0]
        ):
            logger.info("💨 L1 CACHE MISS: No similar documents found.")
            return None

        distance = results["distances"][0][0]
        document = results["documents"][0][0]

        if distance < settings.CACHE_DISTANCE_THRESHOLD:
            logger.warning(
                f"🎯 L1 CACHE HIT! (Semantic Match) Found a similar payload with distance {distance:.4f}."
            )
            return document
        else:
            logger.info(
                f"💨 L1 CACHE MISS. Closest payload distance ({distance:.4f}) is above threshold."
            )
            return None

    except Exception as e:
        logger.error(
            "❌ An error occurred during L1 ChromaDB query. Assuming cache miss.",
            exc_info=True,
        )
        return None


async def add(brief_key: str, payload: Dict):
    """
    Adds or updates a result payload in the cache.

    The payload is stored against a deterministic ID for L0 lookups and is
    associated with a semantic vector of the brief key for L1 lookups.

    Args:
        brief_key: The deterministic, composite key from the user's brief.
        payload: A dictionary containing the 'final_report' and 'cached_results_path'.
    """
    if not _report_collection:
        logger.warning("⚠️ Report collection is not available. Skipping cache add.")
        return

    logger.info("🔥 Adding new payload to Report Cache (L0/L1)...")

    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error(
            "❌ Could not generate embedding for new cache entry. Skipping add."
        )
        return

    payload_json = json.dumps(payload)
    doc_id = str(hash(brief_key))

    try:
        _report_collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[payload_json],
            metadatas=[{"brief_key": brief_key}],
        )
        logger.info(f"✅ Successfully added/updated payload in cache with ID: {doc_id}")
    except Exception as e:
        logger.error("❌ Failed to add document to ChromaDB collection.", exc_info=True)
