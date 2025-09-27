# catalyst/clients/gemini/core.py

"""
The internal core logic for making API calls to the Google Gemini service.
This version is refactored for a clean separation of concerns. Its sole
responsibility is to handle the network communication and retry only on
transient network errors. Content validation is delegated to the higher-level
resilience invoker.
"""
import asyncio
import time
from typing import Optional, List, Dict, Any, Union

from google.genai import types
from pydantic import BaseModel

from .client_instance import client
from .resilience import should_retry, calculate_backoff_delay
from .schema import process_response_schema
from ... import settings
from ...utilities.logger import get_logger

logger = get_logger(__name__)


def _prepare_generation_config(
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]] = None,
) -> types.GenerateContentConfig:
    """Helper to build the single, consolidated generation configuration object."""
    config_params = {}
    processed_schema = process_response_schema(response_schema)
    if response_schema and processed_schema:
        config_params["response_mime_type"] = "application/json"
        config_params["response_schema"] = processed_schema
    elif response_schema and not processed_schema:
        logger.warning(
            "Failed to process schema, continuing without structured output."
        )
    if tools:
        config_params["tools"] = tools
    return types.GenerateContentConfig(**config_params)


async def generate_content_core_async(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
    model_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    The core ASYNCHRONOUS function that makes the API call. It includes a
    retry loop for network-level errors only.
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)
    max_retries = settings.RETRY_NETWORK_ATTEMPTS
    final_model_name = model_name or settings.GEMINI_MODEL_NAME
    logger.info(f"Requesting content from model '{final_model_name}' (native async)...")

    for attempt in range(max_retries):
        try:
            # Make the single, best-effort API call.
            response = await client.aio.models.generate_content(
                model=final_model_name,
                contents=prompt_parts,
                config=generation_config,
            )

            # --- START: RESILIENCE REFACTOR ---
            # The client's job is NOT to validate content. It simply extracts
            # the raw text and returns it. Even if the text is empty or not
            # JSON, it is passed up to the resilience invoker to handle.
            return {"text": response.text if hasattr(response, "text") else None}
            # --- END: RESILIENCE REFACTOR ---

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries}: Async API call failed.",
                exc_info=True,
            )
            # Use the simplified should_retry to check for network errors.
            if not should_retry(e) or attempt == max_retries - 1:
                logger.error(f"API call failed permanently after {max_retries} attempts.")
                # We do not raise here; we return None and let the invoker handle it.
                return None
            await asyncio.sleep(calculate_backoff_delay(attempt))
    return None


def generate_content_core_sync(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
) -> Optional[Dict[str, Any]]:
    """
    The core SYNCHRONOUS function that makes the API call with a retry
    loop for network-level errors only.
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)
    max_retries = settings.RETRY_NETWORK_ATTEMPTS

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt_parts,
                config=generation_config,
            )

            # --- START: RESILIENCE REFACTOR ---
            # Same as the async version: just extract the raw text.
            return {"text": response.text if hasattr(response, "text") else None}
            # --- END: RESILIENCE REFACTOR ---

        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries}: Sync API call failed.",
                exc_info=True,
            )
            if not should_retry(e) or attempt == max_retries - 1:
                logger.error(f"API call failed permanently after {max_retries} attempts.")
                return None
            time.sleep(calculate_backoff_delay(attempt))
    return None
