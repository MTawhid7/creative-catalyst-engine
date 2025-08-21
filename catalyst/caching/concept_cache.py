"""
The Concept Cache: Level 3 Caching Service.

This module manages the semantic cache for creative concepts and their associated
research summaries. This allows the system's knowledge to compound over time,
making future reports on similar concepts faster and more insightful.
"""

import json
from typing import Optional, Dict, List, Union, Any

import chromadb

from .. import settings
from ..clients import gemini_client
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- ChromaDB Client Initialization ---
_collection_name = settings.CHROMA_COLLECTION_NAME + "_concepts"
_concept_collection = None
try:
    chroma_client = chromadb.PersistentClient(path=str(settings.CHROMA_PERSIST_DIR))
    _concept_collection = chroma_client.get_or_create_collection(name=_collection_name)
    logger.info(
        f"Concept Cache (L3) initialized. Collection '{_collection_name}' loaded/created."
    )
except Exception as e:
    logger.critical(
        "CRITICAL: Failed to initialize ChromaDB for Concept Cache. L3 Caching will be disabled.",
        exc_info=True,
    )


async def check(concept: str) -> Optional[List[str]]:
    """
    Checks the L3 cache for existing research summaries related to a creative concept.
    """
    if not _concept_collection:
        return None

    logger.info(f"Checking Concept Cache (L3) for concept: '{concept}'")

    embedding = await gemini_client.generate_embedding_async(concept)
    if not embedding:
        logger.error(
            f"Could not generate embedding for L3 cache check on concept '{concept}'."
        )
        return None

    try:
        results = _concept_collection.query(query_embeddings=[embedding], n_results=5)

        # --- RESILIENCE FIX: Defensively check the structure of the results ---
        if not results or not results.get("ids") or not results["ids"][0]:
            logger.info(f"L3 CACHE MISS: No summaries found for concept '{concept}'.")
            return None

        # Check distances structure step by step (following cache_service.py pattern)
        distances = results.get("distances")
        if (
            not distances
            or len(distances) == 0
            or distances[0] is None
            or len(distances[0]) == 0
        ):
            logger.info("L3 CACHE MISS: No valid distances found for this query.")
            return None

        # Check documents structure step by step (following cache_service.py pattern)
        documents_list = results.get("documents")
        if (
            not documents_list
            or len(documents_list) == 0
            or documents_list[0] is None
            or len(documents_list[0]) == 0
        ):
            logger.info("L3 CACHE MISS: No valid documents found for this query.")
            return None

        distance = distances[0][0]
        documents = documents_list[0]

        if distance < (
            settings.CACHE_DISTANCE_THRESHOLD + 0.1
        ):  # Use a slightly wider threshold
            logger.info(
                f"L3 CACHE HIT! Found {len(documents)} related summaries for concept '{concept}'."
            )
            return documents
        else:
            logger.info(
                f"L3 CACHE MISS. Closest concept distance ({distance:.4f}) is above threshold."
            )
            return None

    except Exception as e:
        logger.error(
            f"An error occurred during L3 ChromaDB query for concept '{concept}'.",
            exc_info=True,
        )
        return None


async def add(concept: str, summaries: List[str]):
    """
    Adds a list of research summaries to the L3 cache, associated with a creative concept.
    """
    if not _concept_collection:
        return

    logger.info(
        f"Adding {len(summaries)} new summaries to Concept Cache (L3) for concept: '{concept}'"
    )

    embedding = await gemini_client.generate_embedding_async(concept)

    # --- RESILIENCE FIX: Guard clause to handle embedding failure ---
    if not embedding:
        logger.error(
            f"Could not generate embedding for new L3 cache entry for '{concept}'. Skipping add."
        )
        return

    # Process each summary individually to avoid type issues
    # Generate individual embeddings for each summary for better semantic accuracy
    for i, summary in enumerate(summaries):
        summary_embedding = await gemini_client.generate_embedding_async(summary)
        if not summary_embedding:
            # Fallback to concept embedding if summary embedding fails
            summary_embedding = embedding

        doc_id = str(hash(concept + summary[:100]))

        # Create metadata dictionary with proper typing
        metadata: Dict[str, Union[str, int, float, bool]] = {"concept": concept}

        try:
            _concept_collection.upsert(
                ids=[doc_id],
                embeddings=[summary_embedding],
                documents=[summary],
                metadatas=[metadata],
            )
        except Exception as e:
            logger.error(
                f"Failed to add summary {i+1} to L3 ChromaDB collection for '{concept}': {e}",
                exc_info=True,
            )

    logger.info(
        f"Successfully processed {len(summaries)} summaries in L3 cache for '{concept}'."
    )
