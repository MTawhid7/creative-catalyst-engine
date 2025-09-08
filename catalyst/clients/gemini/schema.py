# catalyst/clients/gemini/schema.py

"""
Handles the cleaning, processing, and validation of JSON schemas to ensure
compatibility with the Google Gemini API's strict requirements.
"""
from typing import Dict, Any, Optional, Union, List
from pydantic import BaseModel
from ...utilities.logger import get_logger

logger = get_logger(__name__)


def _clean_schema_for_gemini(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively processes a JSON schema to remove unsupported fields and
    handle specific Gemini API constraints.
    """
    if not isinstance(schema, dict):
        return schema

    clean_schema = {}
    if "type" in schema:
        clean_schema["type"] = schema["type"]

    schema_type = schema.get("type")

    if schema_type == "object":
        if "properties" in schema and schema["properties"]:
            clean_properties = {
                key: _clean_schema_for_gemini(value)
                for key, value in schema["properties"].items()
            }
            clean_properties = {
                k: v for k, v in clean_properties.items() if v
            }  # Remove empty results

            if clean_properties:
                clean_schema["properties"] = clean_properties
            else:
                # Workaround for Gemini's "object properties must not be empty" rule
                return {
                    "type": "string",
                    "description": schema.get(
                        "description", "Dynamic object serialized as JSON string"
                    ),
                }

        for field in ["required", "propertyOrdering", "nullable"]:
            if field in schema:
                clean_schema[field] = schema[field]

    elif schema_type == "array":
        if "items" in schema:
            clean_schema["items"] = _clean_schema_for_gemini(schema["items"])
        for field in ["minItems", "maxItems", "nullable"]:
            if field in schema:
                clean_schema[field] = schema[field]

    elif schema_type in ["string", "integer", "number", "boolean"]:
        supported_fields = {
            "string": ["enum", "format", "nullable"],
            "integer": ["format", "minimum", "maximum", "enum", "nullable"],
            "number": ["format", "minimum", "maximum", "enum", "nullable"],
            "boolean": ["nullable"],
        }
        for field in supported_fields.get(schema_type, []):
            if field in schema:
                clean_schema[field] = schema[field]

    for key in ["anyOf", "allOf", "oneOf"]:
        if key in schema:
            cleaned_options = [
                _clean_schema_for_gemini(item) for item in schema[key] if item
            ]
            if cleaned_options:
                clean_schema[key] = cleaned_options

    if "$defs" in schema:
        clean_defs = {
            key: _clean_schema_for_gemini(value)
            for key, value in schema["$defs"].items()
            if value
        }
        if clean_defs:
            clean_schema["$defs"] = clean_defs

    if "description" in schema:
        clean_schema["description"] = schema["description"]

    return clean_schema


def _validate_gemini_schema(schema: Dict[str, Any], path: str = "root") -> List[str]:
    """
    Validates a schema against Gemini API requirements, specifically checking
    for object types with empty properties.
    """
    errors = []
    if not isinstance(schema, dict):
        return errors

    if schema.get("type") == "object" and not schema.get("properties"):
        errors.append(f"Object at {path} has empty properties, which is not allowed.")

    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            errors.extend(
                _validate_gemini_schema(prop_schema, f"{path}.properties.{prop_name}")
            )

    if "items" in schema:
        errors.extend(_validate_gemini_schema(schema["items"], f"{path}.items"))

    return errors


def process_response_schema(
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
    """
    Processes a Pydantic model or dict schema into a Gemini-compatible format.
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

        cleaned_schema = _clean_schema_for_gemini(base_schema)
        validation_errors = _validate_gemini_schema(cleaned_schema)

        if validation_errors:
            logger.error(f"Schema validation failed: {'; '.join(validation_errors)}")
            return None

        return cleaned_schema
    except Exception as e:
        logger.error(f"Failed to process response schema: {e}", exc_info=True)
        return None
