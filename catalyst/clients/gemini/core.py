# catalyst/clients/gemini/core.py

"""
The internal core logic for making API calls to the Google Gemini service.
This version is aligned with the modern google-genai SDK (2025) and hardened
with production-grade resilience patterns.
"""
import json
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


def _process_response(response: Any, has_schema: bool) -> Optional[Dict]:
    """
    Helper to process the raw response from the Gemini API.
    Returns None if the response is empty or malformed.
    """
    if not hasattr(response, "text") or response.text is None:
        logger.warning("API call returned an empty response object.")
        return None

    response_text = response.text.strip()
    if not response_text:
        logger.warning("API call returned empty text content.")
        return None

    if has_schema:
        try:
            if response_text.startswith("```json"):
                response_text = response_text[7:-3].strip()
            return json.loads(response_text)
        except json.JSONDecodeError:
            logger.error("Failed to decode JSON from response.", exc_info=True)
            return None
    else:
        return {"text": response_text}


async def generate_content_core_async(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
) -> Optional[Dict]:
    """The core ASYNCHRONOUS function that makes the API call with retry logic."""
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)
    max_retries = settings.GEMINI_MAX_RETRIES

    for attempt in range(max_retries):
        try:
            response = await client.aio.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt_parts,
                config=generation_config,
            )

            processed = _process_response(response, has_schema=bool(response_schema))
            if processed:
                return processed

            raise RuntimeError("API call returned an empty response object.")

        except Exception as e:
            logger.warning(
                f"Attempt {attempt+1}/{max_retries}: Async API call failed.",
                exc_info=True,
            )
            if not should_retry(e) or attempt == max_retries - 1:
                logger.error(
                    f"API call failed permanently after {max_retries} attempts."
                )
                return None
            await asyncio.sleep(calculate_backoff_delay(attempt))
    return None


def generate_content_core_sync(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
) -> Optional[Dict]:
    """The core SYNCHRONOUS function that makes the API call with retry logic."""
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)
    # --- BUG FIX: The 'max_retries' variable was missing here. ---
    max_retries = settings.GEMINI_MAX_RETRIES

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt_parts,
                config=generation_config,
            )

            processed = _process_response(response, has_schema=bool(response_schema))
            if processed:
                return processed

            raise RuntimeError("API call returned an empty response object.")

        except Exception as e:
            logger.warning(
                f"Attempt {attempt+1}/{max_retries}: Sync API call failed.",
                exc_info=True,
            )
            if not should_retry(e) or attempt == max_retries - 1:
                logger.error(
                    f"API call failed permanently after {max_retries} attempts."
                )
                return None
            time.sleep(calculate_backoff_delay(attempt))
    return None
