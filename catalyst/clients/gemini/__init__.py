# catalyst/clients/gemini/__init__.py

"""
A dedicated, resilient client for all interactions with the Google Gemini API.
This package defines the public-facing functions for the application.
"""

import os
import asyncio
from typing import Optional, List, Dict, Any, Union

from google.genai import types
from pydantic import BaseModel

# This is the architectural switch. It checks the environment variable at import time.
# AFTER
from .core import generate_content_core_async, generate_content_core_sync

from ... import settings
from ...utilities.logger import get_logger
from .client_instance import client
from .core import generate_content_core_async, generate_content_core_sync
from .resilience import should_retry, calculate_backoff_delay

logger = get_logger(__name__)

# --- Public-Facing Functions ---


async def generate_content_async(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]] = None,
    tools: Optional[List[types.Tool]] = None,
    model_name: Optional[str] = None,
) -> Optional[Dict]:
    """Asynchronously runs the API call using the native async method."""
    # --- START: THE DEFINITIVE FIX ---
    # The model_name parameter must be passed down to the core function.
    return await generate_content_core_async(
        prompt_parts, response_schema, tools, model_name
    )
    # --- END: THE DEFINITIVE FIX ---


def generate_content_sync(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]] = None,
    tools: Optional[List[types.Tool]] = None,
) -> Optional[Dict]:
    """Synchronously runs the API call."""
    return generate_content_core_sync(prompt_parts, response_schema, tools)


async def generate_embedding_async(
    text: str, model_name: str = settings.EMBEDDING_MODEL_NAME
) -> Optional[List[float]]:
    """Asynchronously generates a vector embedding using the native async method."""
    if not client:
        logger.error("❌ Cannot generate embedding: Gemini client is not configured.")
        return None

    logger.info(f"🧠 Generating embedding for text: '{text[:70]}...'")
    for attempt in range(3):
        try:
            embedding_config = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")
            result = await client.aio.models.embed_content(
                model=model_name,
                contents=text,
                config=embedding_config,
            )

            if result and result.embeddings and len(result.embeddings) > 0:
                embedding_object = result.embeddings[0]
                if hasattr(embedding_object, "values") and embedding_object.values:
                    return embedding_object.values

            logger.warning(
                "⚠️ Embedding response was successful but contained no values."
            )
            return None
        except Exception as e:
            logger.error(
                f"❌ Attempt {attempt+1}: Embedding generation failed", exc_info=True
            )
            if not should_retry(e) or attempt == 2:
                break
            await asyncio.sleep(calculate_backoff_delay(attempt))

    logger.critical("❌ Could not generate embedding after multiple retries.")
    return None
