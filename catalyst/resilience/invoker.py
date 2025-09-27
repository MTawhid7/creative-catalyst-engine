# catalyst/resilience/invoker.py

"""
This module provides the core resilience layer for all AI interactions.
Its primary component, the `invoke_with_resilience` function, wraps AI calls
in a robust, deterministic sanitization pipeline to ensure a high probability
of receiving a valid, structured response.
"""

import json
from typing import (
    Callable,
    Awaitable,
    Optional,
    Type,
    TypeVar,
    Any,
    get_origin,
    get_args,
    Union,
)
from pydantic import BaseModel, ValidationError

from .exceptions import MaxRetriesExceededError
from ..utilities.logger import get_logger
from ..clients import gemini
from .. import settings

PydanticModel = TypeVar("PydanticModel", bound=BaseModel)
logger = get_logger(__name__)


# --- START: THE DEFINITIVE SANITIZATION PIPELINE ---
def _sanitize_ai_response(data: Any) -> Any:
    """
    Recursively finds and fixes stringified JSON lists/objects within a data structure.
    This is the first sanitization step, correcting the most common AI error.
    """
    if isinstance(data, dict):
        return {k: _sanitize_ai_response(v) for k, v in data.items()}
    if isinstance(data, list):
        return [_sanitize_ai_response(item) for item in data]
    if isinstance(data, str):
        # --- START: FIX 1 ---
        # Check if the string looks like a JSON list OR object.
        if (data.startswith("[") and data.endswith("]")) or (
            data.startswith("{") and data.endswith("}")
        ):
            # --- END: FIX 1 ---
            try:
                # Recursively call the function on the parsed data.
                return _sanitize_ai_response(json.loads(data))
            except json.JSONDecodeError:
                pass  # Not valid JSON, return the original string.
    return data


def _normalize_lists_recursively(data: Any, model: Type[BaseModel]) -> Any:
    """
    Recursively walks the data and ensures that any field defined as a List in
    the Pydantic model is actually a list in the data, wrapping single items.
    """
    if not isinstance(data, dict):
        return data

    for field_name, field_info in model.model_fields.items():
        if field_name not in data or data[field_name] is None:
            continue

        origin = get_origin(field_info.annotation)
        type_args = get_args(field_info.annotation)

        # --- START: FIX 2 ---
        # This check now correctly identifies List and Optional[List] types.
        is_list_field = origin is list
        if origin in (Union, getattr(Union, "__ror__", Union)):  # Handles Python < 3.10
            if any(get_origin(arg) is list for arg in type_args):
                is_list_field = True
        # --- END: FIX 2 ---

        if is_list_field and not isinstance(data[field_name], list):
            data[field_name] = [data[field_name]]

        nested_model = None
        # Use the already calculated type_args
        nested_model_args = [
            arg
            for arg in type_args
            if isinstance(arg, type) and issubclass(arg, BaseModel)
        ]
        if nested_model_args:
            nested_model = nested_model_args[0]
        elif isinstance(field_info.annotation, type) and issubclass(
            field_info.annotation, BaseModel
        ):
            nested_model = field_info.annotation

        if nested_model:
            if isinstance(data[field_name], list):
                data[field_name] = [
                    _normalize_lists_recursively(item, nested_model)
                    for item in data[field_name]
                ]
            elif isinstance(data[field_name], dict):
                data[field_name] = _normalize_lists_recursively(
                    data[field_name], nested_model
                )
    return data


# --- END: THE DEFINITIVE SANITIZATION PIPELINE ---


async def invoke_with_resilience(
    ai_function: Callable[..., Awaitable[Optional[dict]]],
    prompt: str,
    response_schema: Type[PydanticModel],
    **kwargs: Any,
) -> PydanticModel:
    """
    Wraps a generic AI function call with a robust, deterministic sanitization
    and validation pipeline.
    """
    try:
        response_data = await ai_function(
            prompt_parts=[prompt], response_schema=response_schema, **kwargs
        )

        if not response_data or not response_data.get("text"):
            raise ValueError("AI call returned an empty or malformed response object.")

        raw_text = response_data["text"].strip()
        parsed_json = json.loads(raw_text)

        sanitized_json = _sanitize_ai_response(parsed_json)
        final_data = _normalize_lists_recursively(sanitized_json, response_schema)

        validated_model = response_schema.model_validate(final_data)

        logger.info(
            f"✅ Successfully validated AI response against {response_schema.__name__}."
        )
        return validated_model

    except (ValueError, json.JSONDecodeError, ValidationError) as e:
        logger.critical(
            f"CRITICAL: AI response failed validation even after sanitization. Error: {e}"
        )
        failed_response_text = locals().get(
            "raw_text", "Response was empty or not captured."
        )
        logger.warning(
            f"Raw AI response that failed validation: {failed_response_text}"
        )
        raise MaxRetriesExceededError(last_exception=e)
