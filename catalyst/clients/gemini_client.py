"""
A dedicated, resilient client for all interactions with the Google Gemini API.
(Fixed version with proper schema handling - additionalProperties removed)
"""

import asyncio
import json
import random
import time
from typing import Optional, List, Dict, Any, Union

from google import genai
from google.genai import types
from google.genai.types import HarmCategory, HarmBlockThreshold
from pydantic import BaseModel

from .. import settings
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- Client Initialization ---
try:
    if settings.GEMINI_API_KEY:
        # Create the client with API key - this is the correct modern approach
        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("Gemini API client configured successfully.")
    else:
        client = None  # Set to None to cause safe failures in functions
        logger.critical(
            "GEMINI_API_KEY not found in settings. The client will not function."
        )
except Exception as e:
    client = None
    logger.critical(
        f"CRITICAL: Failed to configure Gemini API client: {e}", exc_info=True
    )


def _clean_schema_for_gemini(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively processes a JSON schema to ensure compatibility with the Gemini API.
    Removes unsupported fields like 'additionalProperties' and cleans up Pydantic-specific fields.

    The Gemini API uses a subset of OpenAPI 3.0 Schema and does NOT support:
    - additionalProperties
    - Many other OpenAPI fields
    - Empty properties for object types (objects MUST have non-empty properties)

    Supported fields for each type:
    - string: enum, format, nullable
    - integer: format, minimum, maximum, enum, nullable
    - number: format, minimum, maximum, enum, nullable
    - boolean: nullable
    - array: minItems, maxItems, items, nullable
    - object: properties, required, propertyOrdering, nullable (properties MUST be non-empty)
    """
    if not isinstance(schema, dict):
        return schema

    # Create a clean copy of the schema
    clean_schema = {}

    # Copy the type field (required)
    if "type" in schema:
        clean_schema["type"] = schema["type"]

    # Handle supported fields based on type
    schema_type = schema.get("type")

    if schema_type == "object":
        # For objects: properties, required, propertyOrdering, nullable
        # CRITICAL: Gemini requires non-empty properties for object types
        if "properties" in schema and schema["properties"]:
            clean_properties = {}
            for key, value in schema["properties"].items():
                cleaned_property = _clean_schema_for_gemini(value)
                if cleaned_property:  # Only add non-empty cleaned properties
                    clean_properties[key] = cleaned_property

            # Only add properties if we have at least one valid property
            if clean_properties:
                clean_schema["properties"] = clean_properties
            else:
                # If we end up with no properties, convert to a string type instead
                # This is a workaround for Gemini's requirement
                logger.warning(
                    f"Converting object with empty properties to string type for Gemini compatibility"
                )
                return {
                    "type": "string",
                    "description": schema.get(
                        "description", "Dynamic object serialized as JSON string"
                    ),
                }
        elif schema.get("properties") == {}:
            # Handle explicitly empty properties - convert to string
            logger.warning(
                f"Converting object with explicitly empty properties to string type for Gemini compatibility"
            )
            return {
                "type": "string",
                "description": schema.get(
                    "description", "Dynamic object serialized as JSON string"
                ),
            }
        else:
            # No properties defined at all - convert to string
            logger.warning(
                f"Converting object with no properties to string type for Gemini compatibility"
            )
            return {
                "type": "string",
                "description": schema.get(
                    "description", "Dynamic object serialized as JSON string"
                ),
            }

        if "required" in schema:
            clean_schema["required"] = schema["required"]

        if "propertyOrdering" in schema:
            clean_schema["propertyOrdering"] = schema["propertyOrdering"]

        if "nullable" in schema:
            clean_schema["nullable"] = schema["nullable"]

    elif schema_type == "array":
        # For arrays: minItems, maxItems, items, nullable
        if "items" in schema:
            clean_schema["items"] = _clean_schema_for_gemini(schema["items"])

        for field in ["minItems", "maxItems", "nullable"]:
            if field in schema:
                clean_schema[field] = schema[field]

    elif schema_type in ["string", "integer", "number"]:
        # For string/integer/number: enum, format, nullable, and for numbers: minimum, maximum
        for field in ["enum", "format", "nullable"]:
            if field in schema:
                clean_schema[field] = schema[field]

        if schema_type in ["integer", "number"]:
            for field in ["minimum", "maximum"]:
                if field in schema:
                    clean_schema[field] = schema[field]

    elif schema_type == "boolean":
        # For boolean: nullable
        if "nullable" in schema:
            clean_schema["nullable"] = schema["nullable"]

    # Handle anyOf, allOf, oneOf (recursively clean each option)
    for key in ["anyOf", "allOf", "oneOf"]:
        if key in schema:
            cleaned_options = []
            for item in schema[key]:
                cleaned_item = _clean_schema_for_gemini(item)
                if cleaned_item:  # Only add non-empty cleaned items
                    cleaned_options.append(cleaned_item)
            if cleaned_options:  # Only add if we have valid options
                clean_schema[key] = cleaned_options

    # Recurse into $defs (used by Pydantic V2)
    if "$defs" in schema:
        clean_defs = {}
        for key, value in schema["$defs"].items():
            cleaned_def = _clean_schema_for_gemini(value)
            if cleaned_def:  # Only add non-empty cleaned definitions
                clean_defs[key] = cleaned_def
        if clean_defs:  # Only add $defs if we have valid definitions
            clean_schema["$defs"] = clean_defs

    # Add description if present (generally supported)
    if "description" in schema:
        clean_schema["description"] = schema["description"]

    return clean_schema


def _validate_gemini_schema(schema: Dict[str, Any], path: str = "root") -> List[str]:
    """
    Validates a schema against Gemini API requirements and returns a list of validation errors.
    """
    errors = []

    if not isinstance(schema, dict):
        return errors

    schema_type = schema.get("type")

    # Check for object types with empty properties
    if schema_type == "object":
        properties = schema.get("properties", {})
        if not properties or len(properties) == 0:
            errors.append(
                f"Object at {path} has empty properties - Gemini requires non-empty properties for OBJECT type"
            )

    # Recursively validate properties
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            prop_errors = _validate_gemini_schema(
                prop_schema, f"{path}.properties.{prop_name}"
            )
            errors.extend(prop_errors)

    # Validate array items
    if "items" in schema:
        item_errors = _validate_gemini_schema(schema["items"], f"{path}.items")
        errors.extend(item_errors)

    # Validate anyOf/allOf/oneOf
    for key in ["anyOf", "allOf", "oneOf"]:
        if key in schema:
            for i, option in enumerate(schema[key]):
                option_errors = _validate_gemini_schema(option, f"{path}.{key}[{i}]")
                errors.extend(option_errors)

    # Validate $defs
    if "$defs" in schema:
        for def_name, def_schema in schema["$defs"].items():
            def_errors = _validate_gemini_schema(def_schema, f"{path}.$defs.{def_name}")
            errors.extend(def_errors)

    return errors


def _process_response_schema(
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """
    Processes the response schema to ensure Gemini API compatibility.
    """
    if response_schema is None:
        return None
    try:
        if isinstance(response_schema, dict):
            base_schema = response_schema
        elif issubclass(response_schema, BaseModel):
            base_schema = response_schema.model_json_schema()
        else:
            logger.warning(f"Unsupported schema type: {type(response_schema)}")
            return None

        # Clean the schema for Gemini compatibility
        cleaned_schema = _clean_schema_for_gemini(base_schema)

        # Validate the cleaned schema
        validation_errors = _validate_gemini_schema(cleaned_schema)
        if validation_errors:
            logger.error(f"Schema validation failed: {'; '.join(validation_errors)}")
            return None

        logger.debug(
            f"Original schema keys: {list(base_schema.keys()) if isinstance(base_schema, dict) else 'N/A'}"
        )
        logger.debug(
            f"Cleaned schema keys: {list(cleaned_schema.keys()) if isinstance(cleaned_schema, dict) else 'N/A'}"
        )

        return cleaned_schema
    except Exception as e:
        logger.error(f"Failed to process response schema: {str(e)}", exc_info=True)
        return None


# --- Resilience Helpers ---
def _should_retry(e: Exception) -> bool:
    """Determines if an API error is transient and worth retrying."""
    error_str = str(e).lower()
    retryable_messages = [
        "deadline exceeded",
        "service unavailable",
        "500",
        "503",
        "504",
        "429",
    ]
    return any(msg in error_str for msg in retryable_messages)


def _calculate_backoff_delay(attempt: int) -> float:
    """Calculates exponential backoff delay with jitter."""
    delay = (2**attempt) + random.uniform(0.5, 1.5)
    return min(delay, 60)


# --- Core Synchronous API Function with Retry Logic ---
def _generate_content_sync(
    prompt_parts: List[Any],
    model_name: str,
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
    tools: Optional[List[types.Tool]],
) -> Optional[Dict]:
    """
    The core synchronous function that makes the actual API call with retry logic.
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    # Build the safety settings using the correct enum values
    safety_settings = [
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    # Build the generation config
    config_params = {
        "temperature": 0.2,
        "safety_settings": safety_settings,
    }

    # Process response schema if provided
    processed_schema = None
    if response_schema:
        processed_schema = _process_response_schema(response_schema)
        if processed_schema:
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = processed_schema
            logger.info("Successfully processed response schema for Gemini API")
        else:
            logger.warning(
                "Failed to process response schema, continuing without structured output"
            )

    # Add tools if provided
    if tools:
        config_params["tools"] = tools

    generation_config = types.GenerateContentConfig(**config_params)

    for attempt in range(5):
        try:
            # Use the client.models.generate_content method
            response = client.models.generate_content(
                model=model_name,
                contents=prompt_parts,
                config=generation_config,
            )

            if not hasattr(response, "text") or response.text is None:
                raise RuntimeError(
                    "Empty or invalid response from API (missing text part)"
                )

            response_text = response.text.strip()
            if not response_text:
                raise RuntimeError("Empty response text from API")

            logger.info(f"Successfully received response from model: {model_name}")

            # This logic works for both Pydantic models and dicts
            if response_schema and processed_schema:
                # Clean up any markdown formatting
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Raw response: {response_text}")
                    return None
            else:
                return {"text": response_text}

        except ValueError as e:
            error_msg = str(e)
            if "additional_properties parameter is not supported" in error_msg:
                logger.error(
                    f"Schema compatibility error: {error_msg}. "
                    f"This should not happen with the fixed schema processing."
                )
                return None
            elif "invalid schema" in error_msg.lower():
                logger.error(f"Invalid schema error: {error_msg}")
                return None
            else:
                logger.error(f"ValueError in API call: {error_msg}")
                if not _should_retry(e) or attempt == 4:
                    return None
        except Exception as e:
            logger.error(
                f"Attempt {attempt+1}: API call failed for model {model_name}",
                exc_info=True,
            )
            if not _should_retry(e) or attempt == 4:
                logger.critical(
                    f"Could not get response after multiple retries. Final error: {e}"
                )
                return None

        # Calculate delay and retry
        if attempt < 4:  # Don't sleep on the last attempt
            delay = _calculate_backoff_delay(attempt)
            logger.warning(f"Retrying in {delay:.2f} seconds...")
            time.sleep(delay)

    return None


# --- Asynchronous Wrapper ---
async def generate_content_async(
    prompt_parts: List[Any],
    model_name: str = settings.GEMINI_MODEL_NAME,
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]] = None,
    tools: Optional[List[types.Tool]] = None,
) -> Optional[Dict]:
    """
    Asynchronously runs the synchronous API call in a separate thread to avoid
    blocking the event loop. This is the primary function to be called by other services.
    """
    logger.info(f"Requesting content from model '{model_name}'...")
    try:
        result = await asyncio.to_thread(
            _generate_content_sync, prompt_parts, model_name, response_schema, tools
        )
        return result
    except Exception as e:
        logger.critical(
            f"An unexpected error occurred in the async wrapper: {e}", exc_info=True
        )
        return None


# --- Fully Asynchronous Version ---
async def generate_content_fully_async(
    prompt_parts: List[Any],
    model_name: str = settings.GEMINI_MODEL_NAME,
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]] = None,
    tools: Optional[List[types.Tool]] = None,
) -> Optional[Dict]:
    """
    Fully asynchronous version using client.aio.models.generate_content.
    This avoids the thread overhead but requires the async client.
    """
    if not client:
        logger.error("Cannot generate content: Gemini client is not configured.")
        return None

    logger.info(f"Requesting content from model '{model_name}' (fully async)...")

    # Build the safety settings using the correct enum values
    safety_settings = [
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        types.SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    # Build the generation config
    config_params = {
        "temperature": 0.2,
        "safety_settings": safety_settings,
    }

    # Process response schema if provided
    processed_schema = None
    if response_schema:
        processed_schema = _process_response_schema(response_schema)
        if processed_schema:
            config_params["response_mime_type"] = "application/json"
            config_params["response_schema"] = processed_schema
            logger.info("Successfully processed response schema for Gemini API")
        else:
            logger.warning(
                "Failed to process response schema, continuing without structured output"
            )

    if tools:
        config_params["tools"] = tools

    generation_config = types.GenerateContentConfig(**config_params)

    for attempt in range(5):
        try:
            # Use the async client
            response = await client.aio.models.generate_content(
                model=model_name,
                contents=prompt_parts,
                config=generation_config,
            )

            if not hasattr(response, "text") or response.text is None:
                raise RuntimeError(
                    "Empty or invalid response from API (missing text part)"
                )

            response_text = response.text.strip()
            if not response_text:
                raise RuntimeError("Empty response text from API")

            logger.info(f"Successfully received response from model: {model_name}")

            if response_schema and processed_schema:
                # Clean up any markdown formatting
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]

                try:
                    return json.loads(response_text)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON response: {e}")
                    logger.debug(f"Raw response: {response_text}")
                    return None
            else:
                return {"text": response_text}

        except ValueError as e:
            error_msg = str(e)
            if "additional_properties parameter is not supported" in error_msg:
                logger.error(
                    f"Schema compatibility error: {error_msg}. "
                    f"This should not happen with the fixed schema processing."
                )
                return None
            elif "invalid schema" in error_msg.lower():
                logger.error(f"Invalid schema error: {error_msg}")
                return None
            else:
                logger.error(f"ValueError in API call: {error_msg}")
                if not _should_retry(e) or attempt == 4:
                    return None
        except Exception as e:
            logger.error(
                f"Attempt {attempt+1}: API call failed for model {model_name}",
                exc_info=True,
            )
            if not _should_retry(e) or attempt == 4:
                logger.critical(
                    f"Could not get response after multiple retries. Final error: {e}"
                )
                return None

        # Calculate delay and retry
        if attempt < 4:  # Don't sleep on the last attempt
            delay = _calculate_backoff_delay(attempt)
            logger.warning(f"Retrying in {delay:.2f} seconds...")
            await asyncio.sleep(delay)

    return None


# --- Embedding Function ---
async def generate_embedding_async(
    text: str, model_name: str = settings.EMBEDDING_MODEL_NAME
) -> Optional[List[float]]:
    """
    Asynchronously generates a vector embedding for a given text, using the correct
    and most compatible SDK patterns.
    """
    if not client:
        logger.error("Cannot generate embedding: Gemini client is not configured.")
        return None

    logger.info(f"Generating embedding for text: '{text[:70]}...'")

    # Define the configuration for the embedding request
    embedding_config = types.EmbedContentConfig(task_type="RETRIEVAL_DOCUMENT")

    for attempt in range(3):
        try:
            # The synchronous SDK call is wrapped in asyncio.to_thread.
            # The parameter is `contents` (plural) and takes a list.
            # The task_type is passed inside the `config` object.
            response = await asyncio.to_thread(
                client.models.embed_content,
                model=model_name,
                contents=[text],  # Must be a list
                config=embedding_config,
            )

            # Defensively parse the response to prevent 'NoneType' errors.
            if response and response.embeddings and response.embeddings[0].values:
                return response.embeddings[0].values
            else:
                logger.warning(
                    "Embedding response was successful but contained no embedding values."
                )
                return None

        except Exception as e:
            logger.error(
                f"Attempt {attempt+1}: Embedding generation failed", exc_info=True
            )
            if not _should_retry(e) or attempt == 2:
                logger.critical(
                    f"Could not generate embedding after multiple retries. Final error: {e}"
                )
                return None
            delay = _calculate_backoff_delay(attempt)
            logger.warning(f"Retrying embedding in {delay:.2f} seconds...")
            await asyncio.sleep(delay)
    return None
