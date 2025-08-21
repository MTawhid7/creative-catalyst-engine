"""
The Synthesis Engine: The Creative Director AI for the Catalyst Engine.
(Final version with a three-stage synthesis: Extract, Organize, Structure)
"""

import json
import asyncio
import re
from typing import Optional, Dict, List, Coroutine, Any

from pydantic import BaseModel, ValidationError
from google.genai import types

from .. import settings
from ..caching import cache_manager
from ..clients import gemini_client
from ..prompts import prompt_library
from ..models.trend_report import FashionTrendReport, KeyPieceDetail
from ..services import reporting_service
from ..utilities.logger import get_logger, get_run_id

logger = get_logger(__name__)

# --- Configuration Constants ---
RPM_LIMIT = 10  # Flash model has a higher limit
DELAY_BETWEEN_REQUESTS = 60 / RPM_LIMIT


async def _run_with_delay(coro: Coroutine, delay: float) -> Any:
    """Waits for a specified delay before running a coroutine."""
    await asyncio.sleep(delay)
    return await coro


def _extract_section_from_context(
    context: str, start_keyword: str, end_keywords: List[str]
) -> str:
    """A robust helper to extract a specific section from the pre-structured text."""
    end_pattern = "|".join(re.escape(k) for k in end_keywords)
    pattern = re.compile(
        rf"{re.escape(start_keyword)}(.*?)(?={end_pattern}|$)",
        re.DOTALL | re.IGNORECASE,
    )
    match = pattern.search(context)
    return match.group(1).strip() if match else ""


async def _extract_insights_from_single_url_async(
    brief: Dict, url: str
) -> Optional[str]:
    """
    Stage 3a (Unit of Work): Uses the Gemini 'url_context' tool to read a SINGLE URL.
    This provides maximum fault isolation.
    """
    logger.info(f"Starting insight extraction task for URL: {url[:80]}...")
    prompt = prompt_library.URL_INSIGHTS_EXTRACTION_PROMPT.format(
        theme_hint=brief.get("theme_hint", ""),
        garment_type=brief.get("garment_type", ""),
        urls_list=f"- {url}",
    )
    tools = [types.Tool(url_context=types.UrlContext())]
    response = await gemini_client.generate_content_async(
        prompt_parts=[prompt], tools=tools
    )
    if response and response.get("text"):
        logger.info(f"Successfully extracted insights from URL: {url[:80]}")
        return response["text"]
    else:
        logger.error(
            f"Failed to extract insights from URL: {url[:80]}. It may have been blocked by safety filters."
        )
        return None


async def _prepare_structured_context_async(brief: Dict, research_context: str) -> str:
    """
    Stage 3b: Organizes the raw research into a clean, bulleted list to reduce
    cognitive load for the final JSON generation step.
    """
    logger.info("Starting pre-structuring step to organize research context...")
    prompt = prompt_library.STRUCTURING_PREP_PROMPT.format(
        theme_hint=brief.get("theme_hint", ""),
        garment_type=brief.get("garment_type", ""),
        research_context=research_context,
    )
    response = await gemini_client.generate_content_async(prompt_parts=[prompt])
    if response and response.get("text"):
        logger.info("Successfully created pre-structured context.")
        return response["text"]
    else:
        logger.warning("Pre-structuring step failed. Falling back to raw context.")
        return research_context


async def _structure_report_divide_and_conquer_async(
    brief: Dict, research_context: str
) -> Optional[Dict]:
    """
    The final, most robust structuring method. It breaks the task into smaller,
    more reliable API calls, each with a focused response schema.
    """
    logger.info("Starting the final 'divide and conquer' structuring process...")
    final_report = {}

    # --- STEP 1: Generate Top-Level Fields ---
    logger.info("Step 1: Generating top-level fields...")
    top_level_context = _extract_section_from_context(
        research_context, "Overarching Theme:", ["Accessories:", "Key Piece 1 Name:"]
    )
    if top_level_context:
        top_level_prompt = prompt_library.TOP_LEVEL_SYNTHESIS_PROMPT.format(
            research_context=top_level_context
        )

        class TopLevelModel(BaseModel):
            overarching_theme: str
            cultural_drivers: List[str]
            influential_models: List[str]

        top_level_response = await gemini_client.generate_content_async(
            prompt_parts=[top_level_prompt],
            model_name=settings.GEMINI_MODEL_NAME,  # Use Flash for speed
            response_schema=TopLevelModel,
        )
        if top_level_response:
            final_report.update(top_level_response)
            logger.info("Successfully generated and validated top-level fields.")
        else:
            logger.critical("Failed to generate top-level fields.")
            return None
    else:
        logger.warning("Could not find top-level context. Using defaults.")
        final_report.update(
            {
                "overarching_theme": brief.get("theme_hint", ""),
                "cultural_drivers": [],
                "influential_models": [],
            }
        )

    # --- STEP 2: Generate Accessories ---
    logger.info("Step 2: Generating accessories...")
    accessories_context = _extract_section_from_context(
        research_context, "Accessories:", ["Key Piece 1 Name:"]
    )
    if accessories_context:
        accessories_prompt = prompt_library.ACCESSORIES_SYNTHESIS_PROMPT.format(
            research_context=accessories_context
        )

        class AccessoriesModel(BaseModel):
            accessories: Dict[str, List[str]]

        accessories_response = await gemini_client.generate_content_async(
            prompt_parts=[accessories_prompt],
            model_name=settings.GEMINI_MODEL_NAME,  # Use Flash for speed
            response_schema=AccessoriesModel,
        )
        if accessories_response:
            final_report.update(accessories_response)
            logger.info("Successfully generated accessories.")
        else:
            logger.warning(
                "Failed to generate accessories. Continuing with an empty dictionary."
            )
            final_report["accessories"] = {}
    else:
        logger.warning("Could not find accessories context.")
        final_report["accessories"] = {}

    # --- STEP 3: Generate Key Pieces Individually ---
    logger.info("Step 3: Generating detailed key pieces individually...")
    key_piece_sections = research_context.split("Key Piece ")[1:]
    processed_pieces = []
    if not key_piece_sections:
        logger.warning("No 'Key Piece' sections found in the pre-structured text.")
    else:
        logger.info(
            f"Found {len(key_piece_sections)} key pieces to process individually."
        )
        for i, section in enumerate(key_piece_sections):
            logger.info(f"Processing Key Piece {i + 1}/{len(key_piece_sections)}...")
            key_piece_prompt = prompt_library.KEY_PIECE_SYNTHESIS_PROMPT.format(
                key_piece_context=section
            )

            piece_response = await gemini_client.generate_content_async(
                prompt_parts=[key_piece_prompt],
                response_schema=KeyPieceDetail,
                model_name=settings.GEMINI_MODEL_NAME,  # Use Pro for the most complex part
            )
            if piece_response:
                try:
                    validated_piece = KeyPieceDetail.model_validate(piece_response)
                    processed_pieces.append(validated_piece.model_dump())
                    logger.info(
                        f"Successfully processed and validated Key Piece {i + 1}."
                    )
                except ValidationError as e:
                    logger.warning(f"Validation failed for Key Piece {i + 1}: {e}")
                    reporting_service.save_debug_json(
                        json.dumps(piece_response), 1, f"key_piece_{i+1}"
                    )
            else:
                logger.error(f"Failed to get a response for Key Piece {i + 1}.")

    final_report["detailed_key_pieces"] = processed_pieces

    # --- STEP 4: Add remaining boilerplate fields ---
    final_report["season"] = brief.get("season", "")
    final_report["year"] = brief.get("year", 0)
    final_report["region"] = brief.get("region", "Global")
    final_report["target_model_ethnicity"] = "Diverse"
    final_report["visual_analysis"] = []

    # --- START OF CORRECTION ---
    # This block defensively checks if the 'accessories' field is a string.
    # If it is, it parses the string as JSON, correcting the data type before final validation.
    if "accessories" in final_report and isinstance(final_report["accessories"], str):
        try:
            logger.warning("Accessories field was a string. Attempting to parse JSON.")
            final_report["accessories"] = json.loads(final_report["accessories"])
        except json.JSONDecodeError:
            logger.error(
                "Failed to parse accessories string into a dictionary. Defaulting to empty."
            )
            final_report["accessories"] = {}
    # --- END OF CORRECTION ---

    # --- STEP 5: Final Validation ---
    try:
        FashionTrendReport.model_validate(final_report)
        logger.info("Successfully assembled and validated the final trend report.")
        return final_report
    except ValidationError as e:
        logger.critical(f"The final assembled report failed validation: {e}")
        reporting_service.save_debug_json(json.dumps(final_report), 1, "final_assembly")
        return None


async def synthesize_report_async(
    brief: Dict, processed_sources: List[Dict]
) -> Optional[Dict]:
    """
    The main public function that orchestrates the three-stage synthesis process.
    """
    logger.info("Starting the creative synthesis process...")

    # Stage 3a: Research & Insight Extraction (Individual & Throttled)
    all_urls_to_process = [
        source["url"] for source in processed_sources if "url" in source
    ]
    extracted_insights = ""
    if all_urls_to_process:
        logger.info(f"Processing {len(all_urls_to_process)} URLs individually.")
        logger.info(
            f"Pacing API calls to respect {RPM_LIMIT} RPM limit (1 call every {DELAY_BETWEEN_REQUESTS:.1f}s)."
        )
        extraction_coroutines = [
            _extract_insights_from_single_url_async(brief, url)
            for url in all_urls_to_process
        ]
        delayed_tasks = [
            _run_with_delay(coro, i * DELAY_BETWEEN_REQUESTS)
            for i, coro in enumerate(extraction_coroutines)
        ]
        all_insights_results = await asyncio.gather(*delayed_tasks)
        successful_insights = [insight for insight in all_insights_results if insight]
        if successful_insights:
            extracted_insights = "\n\n---\n\n".join(successful_insights)
            logger.info(
                f"Successfully combined insights from {len(successful_insights)} of {len(all_urls_to_process)} URLs."
            )
        else:
            logger.warning("All URL processing tasks failed to return insights.")

    # Combine with Cached Knowledge
    cached_summaries = []
    concepts_to_check = brief.get("search_keywords", [])
    for concept in concepts_to_check:
        cached_results = await cache_manager.check_concept_cache_async(concept)
        if cached_results:
            cached_summaries.extend(cached_results)

    final_research_context = ""
    if cached_summaries:
        final_research_context += (
            "--- CACHED KNOWLEDGE ---\n" + "\n".join(cached_summaries) + "\n\n"
        )
    if extracted_insights:
        final_research_context += "--- NEW WEB RESEARCH ---\n" + extracted_insights

    if not final_research_context.strip():
        logger.error("Synthesis halted: No research data available.")
        return None

    # Stage 3b: Pre-Structuring (Outlining)
    organized_context = await _prepare_structured_context_async(
        brief, final_research_context
    )

    # Stage 3c: Structuring with "Divide and Conquer"
    final_report = await _structure_report_divide_and_conquer_async(
        brief, organized_context
    )

    if final_report:
        if extracted_insights:
            for concept in concepts_to_check:
                await cache_manager.add_to_concept_cache_async(
                    concept, [extracted_insights]
                )
        return final_report
    else:
        logger.critical(
            "Orchestration halted: Synthesis engine failed to produce a valid report."
        )
        return None
