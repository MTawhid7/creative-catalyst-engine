"""
The Briefing Engine: The Intake Specialist for the Creative Catalyst Engine.
(Upgraded with a resilient, two-stage enrichment process)
"""

import json
from datetime import datetime
from typing import Optional, Dict, List, Any
import asyncio

from ..clients import gemini_client
from ..prompts import prompt_library
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- (BRIEF_SCHEMA remains the same) ---
BRIEF_SCHEMA = [
    {
        "name": "theme_hint",
        "description": "The core creative idea or aesthetic. This is the most important variable.",
        "default": None,
        "is_required": True,
    },
    {
        "name": "garment_type",
        "description": "A specific type of clothing (e.g., 'T-shirt', 'Evening Gown', 'Denim Jacket').",
        "default": None,
    },
    {
        "name": "brand_category",
        "description": "The market tier of the fashion brand (e.g., 'Fast Fashion', 'Contemporary', 'Luxury').",
        "default": "Luxury",
    },
    {
        "name": "target_audience",
        "description": "The intended wearer of the fashion (e.g., 'Gen-Z teenagers', 'Professional women').",
        "default": "Young Women",
    },
    {
        "name": "region",
        "description": "The geographical location or cultural context.",
        "default": None,
    },
    {
        "name": "key_attributes",
        "description": "A list of specific, descriptive attributes or constraints.",
        "default": ["elegant", "stylish"],
    },
    {
        "name": "season",
        "description": "The fashion season, normalized to 'Spring/Summer' or 'Fall/Winter'.",
        "default": "auto",
    },
    {
        "name": "year",
        "description": "The target year for the collection.",
        "default": "auto",
    },
]


# --- (_deconstruct_passage_async remains the same) ---
async def _deconstruct_passage_async(user_passage: str) -> Optional[Dict]:
    """
    Uses a schema-driven prompt to deconstruct the user's passage into a structured dictionary.
    This version correctly parses the JSON string from the model's response.
    """
    logger.info("Deconstructing user passage with schema-driven AI...")

    variable_rules = "\n".join(
        [f"- **{item['name']}**: {item['description']}" for item in BRIEF_SCHEMA]
    )
    prompt = prompt_library.SCHEMA_DRIVEN_DECONSTRUCTION_PROMPT.format(
        variable_rules=variable_rules, user_passage=user_passage
    )

    response_data = await gemini_client.generate_content_async(prompt_parts=[prompt])

    if not response_data or "text" not in response_data:
        logger.error(
            "AI failed to deconstruct the user's brief. The model returned an empty or invalid response."
        )
        return None

    try:
        # The response text is the JSON string we need to parse.
        json_text = response_data["text"]

        # Clean up potential markdown formatting from the model's output.
        if json_text.strip().startswith("```json"):
            json_text = json_text.strip()[7:]
        if json_text.strip().endswith("```"):
            json_text = json_text.strip()[:-3]

        # Parse the cleaned string into a Python dictionary.
        extracted_data = json.loads(json_text)
        return extracted_data

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(
            f"Failed to parse JSON from the model's response. Error: {e}", exc_info=True
        )
        # Log the raw response to help with debugging the model's output format.
        logger.error(f"Raw model response text was: {response_data.get('text')}")
        return None


def _validate_and_apply_defaults(extracted_data: Optional[Dict]) -> Optional[Dict]:
    """
    Validates the extracted data against the schema and applies default values for missing fields.
    """
    if not isinstance(extracted_data, dict):
        extracted_data = {}

    final_brief = {}
    for item in BRIEF_SCHEMA:
        key = item["name"]
        value = extracted_data.get(key)

        if value is None or (isinstance(value, str) and not value.strip()):
            final_brief[key] = item["default"]
        else:
            final_brief[key] = value

    if final_brief.get("season") == "auto":
        current_month = datetime.now().month
        final_brief["season"] = (
            "Spring/Summer" if 4 <= current_month <= 9 else "Fall/Winter"
        )

    # --- START OF CORRECTION ---
    # This block ensures the 'year' field is always an integer.
    year_value = final_brief.get("year")
    if year_value == "auto" or not year_value:
        final_brief["year"] = datetime.now().year
    else:
        try:
            # Attempt to cast the extracted value to an integer.
            final_brief["year"] = int(year_value)
        except (ValueError, TypeError):
            # If casting fails, log a warning and fall back to the current year.
            logger.warning(
                f"Could not parse '{year_value}' as a year. Defaulting to current year."
            )
            final_brief["year"] = datetime.now().year
    # --- END OF CORRECTION ---

    for item in BRIEF_SCHEMA:
        if item.get("is_required") and not final_brief.get(item["name"]):
            logger.critical(
                f"Could not extract required variable '{item['name']}' from the passage."
            )
            return None

    return final_brief


# --- (Remaining functions _get_enrichment_data_async, _parse_llm_creative_output, _enrich_brief_async, create_enriched_brief_async are unchanged) ---
async def _get_enrichment_data_async(
    initial_prompt: str,
    correction_prompt_template: str,
    prompt_args: Dict,
    task_name: str,
) -> Optional[str]:
    """
    A resilient helper function that attempts to get enrichment data, and re-queries
    with a correction prompt if the first attempt fails.
    """
    # First attempt
    logger.info(f"Attempting to generate {task_name} (Attempt 1)...")
    initial_response = await gemini_client.generate_content_async(
        prompt_parts=[initial_prompt]
    )

    if (
        initial_response
        and initial_response.get("text")
        and initial_response["text"].strip()
    ):
        logger.info(f"Successfully generated {task_name} on the first attempt.")
        return initial_response["text"].strip()

    # If first attempt fails, trigger the correction prompt
    logger.warning(
        f"First attempt to generate {task_name} failed or returned empty. Triggering self-correction."
    )
    failed_output = initial_response.get("text", "None") if initial_response else "None"

    correction_prompt = correction_prompt_template.format(
        failed_output=failed_output, **prompt_args
    )

    logger.info(f"Attempting to generate {task_name} (Attempt 2 - Correction)...")
    correction_response = await gemini_client.generate_content_async(
        prompt_parts=[correction_prompt]
    )

    if (
        correction_response
        and correction_response.get("text")
        and correction_response["text"].strip()
    ):
        logger.info(f"Successfully generated {task_name} on the second attempt.")
        return correction_response["text"].strip()

    logger.critical(
        f"Self-correction also failed for {task_name}. The model could not produce a valid output."
    )
    return None


def _parse_llm_creative_output(text: Optional[str], expected_key: str) -> Any:
    """
    Robustly parses the raw text output from an LLM for creative enrichment.
    It handles plain text, comma-separated lists, and unexpected JSON with markdown.
    """
    if not text:
        return None

    cleaned_text = text.strip().removeprefix("```json").removesuffix("```").strip()

    try:
        data = json.loads(cleaned_text)
        # If successful, extract the value from the expected key
        return data.get(expected_key)
    except (json.JSONDecodeError, AttributeError):
        # If it's not valid JSON, return the cleaned text as-is
        return cleaned_text


async def _enrich_brief_async(brief: Dict) -> Dict:
    """
    Expands the brief with AI-driven creative concepts, a strategic antagonist,
    and searchable keywords using a resilient, two-stage process.
    """
    logger.info("Enriching the creative brief with AI-driven concepts...")

    # Prepare arguments for both initial and correction prompts
    concept_prompt_args = {
        "theme_hint": brief.get("theme_hint", "general fashion"),
        "garment_type": brief.get("garment_type", "clothing"),
        "key_attributes": ", ".join(brief.get("key_attributes", [])),
    }
    antagonist_prompt_args = {"theme_hint": brief.get("theme_hint", "general fashion")}

    # Define the initial prompts
    initial_expansion_prompt = prompt_library.THEME_EXPANSION_PROMPT.format(
        **concept_prompt_args
    )
    initial_antagonist_prompt = prompt_library.CREATIVE_ANTAGONIST_PROMPT.format(
        **antagonist_prompt_args
    )

    # Create concurrent tasks using the resilient helper function
    expansion_task = _get_enrichment_data_async(
        initial_expansion_prompt,
        prompt_library.CONCEPTS_CORRECTION_PROMPT,
        concept_prompt_args,
        "concepts",
    )
    antagonist_task = _get_enrichment_data_async(
        initial_antagonist_prompt,
        prompt_library.ANTAGONIST_CORRECTION_PROMPT,
        antagonist_prompt_args,
        "antagonist",
    )

    concepts_output, antagonist_output = await asyncio.gather(
        expansion_task, antagonist_task
    )

    # Use the new robust parsing logic on the results
    parsed_concepts = _parse_llm_creative_output(concepts_output, "concepts")
    if isinstance(parsed_concepts, list):
        brief["expanded_concepts"] = parsed_concepts
    elif isinstance(parsed_concepts, str):
        brief["expanded_concepts"] = [
            c.strip() for c in parsed_concepts.split(",") if c.strip()
        ]
    else:
        brief["expanded_concepts"] = []

    parsed_antagonist = _parse_llm_creative_output(antagonist_output, "antagonist")
    brief["creative_antagonist"] = (
        parsed_antagonist if isinstance(parsed_antagonist, str) else None
    )

    logger.info(f"Brief expanded with concepts: {brief.get('expanded_concepts')}")
    logger.info(f"Creative antagonist identified: {brief.get('creative_antagonist')}")

    # --- Keyword Extraction Step with Uniqueness ---
    # Use a set for automatic de-duplication
    search_keywords = set()
    if brief.get("theme_hint"):
        search_keywords.add(brief["theme_hint"])

    if brief.get("expanded_concepts"):
        extraction_prompt = prompt_library.KEYWORD_EXTRACTION_PROMPT.format(
            concepts_list=json.dumps(brief["expanded_concepts"])
        )
        keyword_response = await gemini_client.generate_content_async(
            prompt_parts=[extraction_prompt]
        )

        if keyword_response and keyword_response.get("text"):
            try:
                # Use the robust parser for the keyword response as well
                keyword_data = _parse_llm_creative_output(
                    keyword_response["text"], "keywords"
                )
                if isinstance(keyword_data, list):
                    search_keywords.update(keyword_data)
            except json.JSONDecodeError:
                logger.warning("Could not parse JSON from keyword extraction response.")

    brief["search_keywords"] = list(search_keywords)

    logger.info(
        f"Extracted search keywords for research: {brief.get('search_keywords')}"
    )

    return brief


async def create_enriched_brief_async(user_passage: str) -> Optional[Dict]:
    """
    The main public function that orchestrates the entire briefing process.
    """
    logger.info("Starting the intelligent briefing process...")

    extracted_data = await _deconstruct_passage_async(user_passage)

    initial_brief = _validate_and_apply_defaults(extracted_data)
    if not initial_brief:
        logger.critical(
            "Briefing process failed during validation and default application."
        )
        return None

    enriched_brief = await _enrich_brief_async(initial_brief)

    logger.info("Intelligent briefing process completed successfully.")
    return enriched_brief
