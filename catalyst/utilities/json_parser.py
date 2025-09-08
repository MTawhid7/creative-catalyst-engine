# catalyst/utilities/json_parser.py

"""
Provides robust utility functions for parsing structured data from
unstructured or semi-structured text, particularly from LLM outputs.
"""

import json
import re
from typing import Optional, Any

from .logger import get_logger

logger = get_logger(__name__)


def parse_json_from_llm_output(llm_output: str) -> Optional[Any]:
    """
    A robust function to extract and parse a JSON object from a string that may
    contain other text, such as reasoning blocks or Markdown fences.

    It attempts to find JSON in a prioritized order:
    1. A JSON object wrapped in ```json ... ``` Markdown fences.
    2. A raw JSON object starting with '{' and ending with '}'.

    Args:
        llm_output: The raw text output from the language model.

    Returns:
        The parsed Python object (dict or list) if found, otherwise None.
    """
    if not llm_output or not isinstance(llm_output, str):
        return None

    # 1. Prioritize the Markdown code fence pattern
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", llm_output, re.DOTALL)
    if json_match:
        json_str = json_match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            logger.error(
                "🛑 Failed to parse extracted JSON string from Markdown fence.",
                exc_info=True,
                extra={"json_string": json_str},
            )
            return None

    # 2. Fallback to finding the first '{' and last '}'
    try:
        json_start = llm_output.find("{")
        json_end = llm_output.rfind("}")
        if json_start != -1 and json_end != -1 and json_end > json_start:
            json_str = llm_output[json_start : json_end + 1]
            return json.loads(json_str)
    except json.JSONDecodeError:
        logger.error(
            "🛑 Failed to parse extracted JSON string from raw text.",
            exc_info=True,
            extra={"raw_text": llm_output},
        )

    logger.warning("⚠️ No valid JSON object found in the AI response.")
    return None
