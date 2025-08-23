"""
The Report Cache: Level 1 Caching Service.

This module manages the semantic cache for complete, final FashionTrendReport objects.
It checks for semantically similar creative briefs to return fully completed reports,
offering the fastest path to a result and avoiding the entire generation workflow.
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
_collection_name = settings.CHROMA_COLLECTION_NAME + "_reports"
_report_collection = None
try:
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    _report_collection = chroma_client.get_or_create_collection(name=_collection_name)
    logger.info(
        f"✅ Report Cache (L1) initialized. Collection '{_collection_name}' loaded/created."
    )
except Exception as e:
    logger.critical(
        "❌ CRITICAL: Failed to initialize ChromaDB for Report Cache. L1 Caching will be disabled.",
        exc_info=True,
    )


async def check(brief_key: str) -> Optional[str]:
    """
    Checks the L1 cache for a semantically similar report using the brief's composite key.
    Returns the JSON string of the report if a close match is found, otherwise None.
    """
    if not _report_collection:
        logger.warning("⚠️ Report collection is not available. Skipping cache check.")
        return None

    logger.info("⚙️ Checking Report Cache (L1) for similar briefs...")

    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error(
            "❌ Could not generate embedding for L1 cache check. Skipping cache."
        )
        return None

    try:
        results = _report_collection.query(query_embeddings=[embedding], n_results=1)

        # --- Defensive Parsing of Results ---
        if not results or not results.get("ids") or not results["ids"][0]:
            logger.info("💨 L1 CACHE MISS: No similar documents found in the cache.")
            return None

        distances = results.get("distances")
        if not distances or not distances[0]:
            logger.info("💨 L1 CACHE MISS: No valid distances found for this query.")
            return None

        documents = results.get("documents")
        if not documents or not documents[0]:
            logger.info("💨 L1 CACHE MISS: No valid documents found for this query.")
            return None

        distance = distances[0][0]
        document = documents[0][0]

        if distance < settings.CACHE_DISTANCE_THRESHOLD:
            logger.warning(
                f"🎯 L1 CACHE HIT! Found a similar report with distance {distance:.4f}."
            )
            return document
        else:
            logger.info(
                f"💨 L1 CACHE MISS. Closest report distance ({distance:.4f}) is above the threshold."
            )
            return None

    except Exception as e:
        logger.error(
            "❌ An error occurred during L1 ChromaDB query. Assuming cache miss.",
            exc_info=True,
        )
        return None


async def add(brief_key: str, report_data: Dict):
    """
    Adds a newly generated report to the L1 cache. The report data is
    stored as a JSON string, associated with the semantic vector of the brief key.
    """
    if not _report_collection:
        logger.warning("⚠️ Report collection is not available. Skipping cache add.")
        return

    logger.info("📥 Adding new report to Report Cache (L1)...")

    embedding = await gemini_client.generate_embedding_async(brief_key)
    if not embedding:
        logger.error(
            "❌ Could not generate embedding for new L1 cache entry. Skipping add."
        )
        return

    report_json = json.dumps(report_data)
    doc_id = str(hash(brief_key))

    try:
        _report_collection.upsert(
            ids=[doc_id],
            embeddings=[embedding],
            documents=[report_json],
            metadatas=[{"brief_key": brief_key}],
        )
        logger.info(
            f"✅ Successfully added/updated report in L1 cache with ID: {doc_id}"
        )
    except Exception as e:
        logger.error(
            "❌ Failed to add document to L1 ChromaDB collection.", exc_info=True
        )
