# catalyst/clients/gemini/core.py

"""
The internal core logic for making API calls to the Google Gemini service.
This version is refactored for a clean separation of concerns and implements
a robust, model-failover resilience strategy.
"""
import asyncio
import time
from typing import Optional, List, Dict, Any, Union

from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
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
    if tools:
        config_params["tools"] = tools
    config_params["safety_settings"] = [
        types.SafetySetting(category=cat, threshold=HarmBlockThreshold.BLOCK_NONE)
        for cat in [
            HarmCategory.HARM_CATEGORY_HARASSMENT,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        ]
    ]
    return types.GenerateContentConfig(**config_params)


# --- START: THE DEFINITIVE, MODEL-FAILOVER REFACTOR ---


async def _attempt_generation_for_model(
    model_to_try: str,
    prompt_parts: List[Any],
    generation_config: types.GenerateContentConfig,
) -> Optional[types.GenerateContentResponse]:
    """
    A helper that attempts to generate content from a specific model,
    with a self-contained retry loop for transient errors.
    """
    for attempt in range(settings.MODEL_RETRY_ATTEMPTS):
        try:
            logger.info(
                f"Requesting content from model '{model_to_try}' (Attempt {attempt + 1}/{settings.MODEL_RETRY_ATTEMPTS})..."
            )
            response = await client.aio.models.generate_content(
                model=model_to_try,
                contents=prompt_parts,
                config=generation_config,
            )
            return response
        except Exception as e:
            logger.warning(
                f"API call for model '{model_to_try}' failed on attempt {attempt + 1}.",
                exc_info=True,
            )
            if not should_retry(e) or attempt == settings.MODEL_RETRY_ATTEMPTS - 1:
                logger.error(
                    f"Model '{model_to_try}' failed permanently after {settings.MODEL_RETRY_ATTEMPTS} attempts."
                )
                return None
            await asyncio.sleep(calculate_backoff_delay(attempt))
    return None


async def generate_content_core_async(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
    model_name: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    The core ASYNCHRONOUS function that makes the API call. It now includes a
    two-stage, model-failover resilience strategy.
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)

    primary_model = model_name or settings.GEMINI_MODEL_NAME
    fallback_model = (
        settings.GEMINI_PRO_MODEL_NAME
        if primary_model == settings.GEMINI_MODEL_NAME
        else settings.GEMINI_MODEL_NAME
    )

    # Stage 1: Attempt generation with the primary model
    response = await _attempt_generation_for_model(
        primary_model, prompt_parts, generation_config
    )
    if response:
        return {"text": response.text if hasattr(response, "text") else None}

    # Stage 2: If the primary model fails, failover to the fallback model
    logger.warning(
        f"Primary model '{primary_model}' failed. Failing over to '{fallback_model}'."
    )
    fallback_response = await _attempt_generation_for_model(
        fallback_model, prompt_parts, generation_config
    )
    if fallback_response:
        return {
            "text": (
                fallback_response.text if hasattr(fallback_response, "text") else None
            )
        }

    logger.critical(
        "CRITICAL: Both primary and fallback models failed to generate a response."
    )
    return None


# --- END: THE DEFINITIVE, MODEL-FAILOVER REFACTOR ---


def generate_content_core_sync(
    prompt_parts: List[Any],
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
) -> Optional[Dict[str, Any]]:
    """
    The core SYNCHRONOUS function. (Note: Not updated with failover logic as
    the application is fully async.)
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    generation_config = _prepare_generation_config(response_schema, tools)
    max_retries = settings.MODEL_RETRY_ATTEMPTS

    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL_NAME,
                contents=prompt_parts,
                config=generation_config,
            )
            return {"text": response.text if hasattr(response, "text") else None}
        except Exception as e:
            logger.warning(
                f"Attempt {attempt + 1}/{max_retries}: Sync API call failed.",
                exc_info=True,
            )
            if not should_retry(e) or attempt == max_retries - 1:
                logger.error(
                    f"API call failed permanently after {max_retries} attempts."
                )
                return None
            time.sleep(calculate_backoff_delay(attempt))
    return None
