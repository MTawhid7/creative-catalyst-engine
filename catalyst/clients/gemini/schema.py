# catalyst/clients/gemini/schema.py

"""
Handles the cleaning, processing, and validation of JSON schemas to ensure
compatibility with the Google Gemini API's strict requirements.
"""
from typing import Dict, Any, Optional, TypeVar, Union, List, Set
from pydantic import BaseModel
from ...utilities.logger import get_logger

logger = get_logger(__name__)

# Define a TypeVar for Pydantic models. This is the correct way to create
# generic functions that operate on any BaseModel subclass.
PydanticModel = TypeVar("PydanticModel", bound=BaseModel)

# --- START: THE DEFINITIVE, ARCHITECTURALLY CORRECT FIX ---


def _clean_schema_recursively(
    schema: Dict[str, Any], pruned_defs: Set[str]
) -> Optional[Dict[str, Any]]:
    """
    The recursive core of the cleaner. It processes a schema object,
    pruning invalid parts and checking for refs to already pruned definitions.
    """
    if not isinstance(schema, dict):
        return schema

    # Pruning condition 1: A property that references a definition that
    # has already been pruned is invalid.
    if "$ref" in schema:
        ref_name = schema["$ref"].split("/")[-1]
        if ref_name in pruned_defs:
            return None

    clean_schema = {}
    for key, value in schema.items():
        if isinstance(value, dict):
            cleaned_value = _clean_schema_recursively(value, pruned_defs)
            if cleaned_value is not None:
                clean_schema[key] = cleaned_value
        elif isinstance(value, list):
            cleaned_list = [
                item
                for item in (_clean_schema_recursively(i, pruned_defs) for i in value)
                if item is not None
            ]
            if cleaned_list:
                clean_schema[key] = cleaned_list
        else:
            clean_schema[key] = value

    # Pruning condition 2: An object with no properties is invalid.
    # This must be checked *after* its children have been processed.
    if clean_schema.get("type") == "object" and not clean_schema.get("properties"):
        logger.warning(
            f"Pruning an object with empty properties: {clean_schema.get('description', '')}"
        )
        return None

    return clean_schema


def _clean_schema_for_gemini(schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    A robust, multi-pass function to process a JSON schema to be compatible
    with the Gemini API. It handles nested Pydantic models by first cleaning
    their definitions and then pruning any properties that reference them.
    """
    pruned_defs: Set[str] = set()

    # Pass 1: Clean the definitions in '$defs'.
    if "$defs" in schema:
        cleaned_defs = {}
        for def_name, def_schema in schema["$defs"].items():
            # In this first pass, we don't have any pruned_defs yet.
            cleaned_def = _clean_schema_recursively(def_schema, set())
            if cleaned_def:
                cleaned_defs[def_name] = cleaned_def
            else:
                # Keep track of which definitions were completely pruned.
                pruned_defs.add(def_name)

        if cleaned_defs:
            schema["$defs"] = cleaned_defs
        else:
            # If all definitions were pruned, remove the '$defs' key entirely.
            del schema["$defs"]

    # Pass 2: Clean the main schema body, now aware of the pruned definitions.
    return _clean_schema_recursively(schema, pruned_defs)


# --- END: THE DEFINITIVE, ARCHITECTURALLY CORRECT FIX ---


def _validate_gemini_schema(schema: Dict[str, Any], path: str = "root") -> List[str]:
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
    if "items" in schema and isinstance(schema["items"], dict):
        errors.extend(_validate_gemini_schema(schema["items"], f"{path}.items"))
    return errors


def process_response_schema(
    response_schema: Optional[Union[type[BaseModel], Dict[str, Any]]],
) -> Optional[Dict[str, Any]]:
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

        if not cleaned_schema:
            logger.warning("Schema became empty after cleaning process.")
            return None

        validation_errors = _validate_gemini_schema(cleaned_schema)
        if validation_errors:
            logger.error(
                f"Schema validation failed after cleaning: {'; '.join(validation_errors)}"
            )
            return None

        return cleaned_schema
    except Exception as e:
        logger.error(f"Failed to process response schema: {e}", exc_info=True)
        return None
