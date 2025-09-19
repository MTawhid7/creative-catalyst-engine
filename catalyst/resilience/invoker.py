# catalyst/resilience/invoker.py

import json
from typing import Callable, Awaitable, Optional, Type, TypeVar
from pydantic import BaseModel, ValidationError

from .exceptions import MaxRetriesExceededError
from catalyst.utilities.logger import get_logger
from catalyst.utilities.json_parser import parse_json_from_llm_output

from catalyst.clients import gemini
from catalyst import settings
from catalyst.prompts import prompt_library

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)
logger = get_logger(__name__)


async def _run_simplifier_layer(
    prompt: str,
    response_schema: Type[PydanticModel],
) -> Optional[PydanticModel]:
    try:
        critical_fields = list(response_schema.model_fields.keys())[:2]
        logger.info(
            f"Attempting to simplify schema to its core fields: {critical_fields}"
        )
        simplifier_prompt = prompt_library.SIMPLIFIER_PROMPT.format(
            prompt=prompt, critical_fields=critical_fields
        )
        response_data = await gemini.generate_content_async(
            prompt_parts=[simplifier_prompt]
        )
        if not response_data or "text" not in response_data:
            return None
        parsed_json = parse_json_from_llm_output(response_data["text"])
        if not parsed_json:
            return None
        model_instance = response_schema.model_validate(parsed_json, strict=False)
        logger.info("✅ Resilience Layer 3 (Simplifier) succeeded.")
        return model_instance
    except Exception as e:
        logger.error(f"❌ Resilience Layer 3 (Simplifier) failed: {e}")
        return None


async def _run_fallback_layer(
    prompt: str,
    response_schema: Type[PydanticModel],
) -> Optional[PydanticModel]:
    try:
        primary_field = list(response_schema.model_fields.keys())[0]
        logger.info(
            f"Attempting to generate a fallback string for primary field: '{primary_field}'"
        )
        fallback_prompt = prompt_library.FALLBACK_PROMPT.format(prompt=prompt)
        response_data = await gemini.generate_content_async(
            prompt_parts=[fallback_prompt]
        )
        if not response_data or "text" not in response_data:
            return None
        model_instance = response_schema.model_validate(
            {primary_field: response_data["text"]}, strict=False
        )
        logger.info("✅ Resilience Layer 4 (Fallback) succeeded.")
        return model_instance
    except Exception as e:
        logger.error(f"❌ Resilience Layer 4 (Fallback) failed: {e}")
        return None


async def invoke_with_resilience(
    ai_function: Callable[..., Awaitable[Optional[dict]]],
    prompt: str,
    response_schema: Type[PydanticModel],
    max_retries: int = settings.RESILIENCE_MAX_RETRIES,
) -> PydanticModel:
    """
    Wraps an AI call with a multi-layer resilience strategy.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries + 1):
        is_retry = attempt > 0
        current_prompt = prompt

        if is_retry and last_error:
            logger.warning(f"Retrying AI call (Attempt {attempt}/{max_retries})...")
            # --- START: REFACTOR ---
            # Layer 2: The Re-Formatter now uses the robust, centralized prompt.
            current_prompt = prompt_library.REFORMATTER_PROMPT.format(
                prompt=prompt,
                failed_response=getattr(last_error, "response_text", "N/A"),
                error_message=str(last_error),
            )
            # --- END: REFACTOR ---

        try:
            response_data = await ai_function(prompt_parts=[current_prompt])

            # Layer 1: The Validator
            if (
                not response_data
                or "text" not in response_data
                or not response_data["text"].strip()
            ):
                raise ValueError(
                    "AI call returned an empty or malformed response object."
                )

            raw_text = response_data["text"]
            parsed_json = parse_json_from_llm_output(raw_text)
            if not parsed_json:
                raise json.JSONDecodeError(
                    f"Could not parse JSON from response: {raw_text}", raw_text, 0
                )

            validated_model = response_schema.model_validate(parsed_json)
            logger.info(
                f"Successfully validated AI response against {response_schema.__name__}."
            )
            return validated_model

        except (ValueError, json.JSONDecodeError, ValidationError) as e:
            logger.warning(f"Resilience Layer 1 (Validator) failed: {e}")
            last_error = e
            if (
                isinstance(e, (json.JSONDecodeError, ValidationError))
                and "raw_text" in locals()
            ):
                e.response_text = raw_text  # type: ignore

    logger.warning(
        f"All {max_retries + 1} attempts to get a valid structured response failed."
    )
    final_error = last_error or ValueError("Unknown validation error after retries.")

    # Layer 3: The Simplifier
    logger.info("Escalating to Resilience Layer 3: The Simplifier.")
    simplified_result = await _run_simplifier_layer(prompt, response_schema)
    if simplified_result:
        return simplified_result

    # Layer 4: The Intelligent Fallback
    logger.info("Escalating to Resilience Layer 4: The Intelligent Fallback.")
    fallback_result = await _run_fallback_layer(prompt, response_schema)
    if fallback_result:
        return fallback_result

    raise MaxRetriesExceededError(last_exception=final_error)
