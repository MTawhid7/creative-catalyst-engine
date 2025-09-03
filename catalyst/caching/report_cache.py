# catalyst/caching/report_cache.py

"""
The L1 Semantic Report Cache.

This module manages the cache for complete, final report payloads using a
vector-based semantic search. Its purpose is to act as a pipeline consistency
checkpoint, ensuring that if two different user requests are interpreted by the
briefing stage to have the same core meaning, the final (and expensive)
synthesis and image generation steps are skipped.
"""

import json
from typing import Optional, Dict

import chromadb

from .. import settings
from ..clients import gemini_client
from ..utilities.logger import get_logger

logger = get_logger(__name__)

# --- ChromaDB Client Initialization ---
_collection_name = settings.CHROMA_COLLECTION_NAME
_report_collection = None
try:
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    _report_collection = chroma_client.get_or_create_collection(name=_collection_name)
    logger.info(
        f"✅ L1 Semantic Cache initialized. Collection '{_collection_name}' loaded/created."
    )
except Exception as e:
    logger.critical(
        "⚠ CRITICAL: Failed to initialize ChromaDB. L1 Caching will be disabled.",
        exc_info=True,
    )


async def check(brief_key: str) -> Optional[str]:
    """
    Checks the L1 semantic cache for a similar report payload.

    Args:
        brief_key: The deterministic, composite key generated from the enriched brief.

    Returns:
        The JSON string of the cached payload if a close semantic match is found,
        otherwise None.
    """
    if not _report_collection:
        logger.warning("⚠️ L1 collection not available. Skipping semantic cache check.")
        return None

    # --- This is now ONLY an L1 Semantic Cache Check ---
    logger.info("⚙️ Checking L1 Semantic Cache...")
    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error("⚠ Could not generate embedding for L1 cache check. Skipping.")
        return None

    try:
        results = _report_collection.query(query_embeddings=[embedding], n_results=1)

        # Check if results exist and have the expected structure
        documents = results.get("documents")
        distances = results.get("distances")

        if (
            not results
            or not documents
            or not distances
            or len(documents) == 0
            or len(distances) == 0
            or len(documents[0]) == 0
            or len(distances[0]) == 0
        ):
            logger.info("💨 L1 CACHE MISS: No similar documents found.")
            return None

        distance = distances[0][0]
        document = documents[0][0]

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
            "⚠ An error occurred during L1 ChromaDB query. Assuming cache miss.",
            exc_info=True,
        )
        return None


async def add(brief_key: str, payload: Dict):
    """
    Adds or updates a result payload in the L1 semantic cache.
    """
    if not _report_collection:
        logger.warning("⚠️ L1 collection not available. Skipping cache add.")
        return

    logger.info("🔥 Adding new payload to L1 Semantic Cache...")

    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error("⚠ Could not generate embedding for new cache entry. Skipping.")
        return

    payload_json = json.dumps(payload)
    # The doc_id is still a hash of the key, which is a robust way to manage upserts.
    doc_id = str(hash(brief_key))

    try:
        _report_collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[payload_json],
            metadatas=[{"brief_key": brief_key}],
        )
        logger.info(
            f"✅ Successfully added/updated payload in L1 cache with ID: {doc_id}"
        )
    except Exception as e:
        logger.error("⚠ Failed to add document to ChromaDB collection.", exc_info=True)
