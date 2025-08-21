"""
The Orchestrator: The Conductor of the Creative Catalyst Engine.
(Definitive version with corrected engine calls and a streamlined workflow)
"""

import json
from ..core import briefing_engine, discovery_engine, synthesis_engine
from ..services import reporting_service
from ..caching import cache_manager
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)


async def run(user_passage: str):
    """
    Executes the full, end-to-end "Direct AI Synthesis" workflow.
    """
    try:
        # --- Stage 1: The "Intelligent Brief" Engine ---
        logger.info("--- STAGE 1: BRIEFING ---")
        enriched_brief = await briefing_engine.create_enriched_brief_async(user_passage)
        if not enriched_brief:
            logger.critical(
                "Orchestration halted: Briefing engine failed to produce a valid brief."
            )
            return

        # --- Level 1 Cache Check: The Fastest Path ---
        logger.info("--- Checking L1 Report Cache ---")
        cached_report_json = await cache_manager.check_report_cache_async(
            enriched_brief
        )
        if cached_report_json:
            logger.warning("--- L1 CACHE HIT: Full workflow bypassed. ---")
            final_report_data = json.loads(cached_report_json)
            reporting_service.generate_outputs(final_report_data, enriched_brief)
            logger.info("Orchestration completed successfully from L1 Cache.")
            return

        # --- Stage 2: The "Discovery" Engine ---
        logger.info("--- STAGE 2: DISCOVERY ---")
        urls_to_analyze = await discovery_engine.discover_urls_async(enriched_brief)

        # --- START OF CHANGE ---
        # This block correctly transforms the list of URL strings from the discovery
        # engine into the List[Dict] format required by the synthesis engine.
        processed_sources = []
        if urls_to_analyze:
            processed_sources = [{"url": u} for u in urls_to_analyze]
        else:
            logger.warning(
                "Discovery engine found no URLs. Proceeding to synthesis with AI's internal knowledge only."
            )
        # --- END OF CHANGE ---

        # --- Stage 3 & 4: The "Synthesis" Engine ---
        logger.info("--- STAGE 3 & 4: DIRECT AI SYNTHESIS ---")
        # The 'processed_sources' variable is now correctly formatted.
        final_report_data = await synthesis_engine.synthesize_report_async(
            enriched_brief, processed_sources
        )
        if not final_report_data:
            logger.critical(
                "Orchestration halted: Synthesis engine failed to produce a valid report."
            )
            return

        # --- Stage 5: The "Reporting" and Caching Engine ---
        logger.info("--- STAGE 5: REPORTING & CACHING ---")
        reporting_service.generate_outputs(final_report_data, enriched_brief)

        await cache_manager.add_to_report_cache_async(enriched_brief, final_report_data)

        logger.info("Orchestration completed successfully.")

    except Exception as e:
        logger.critical(
            f"A critical, unhandled exception occurred in the orchestrator: {e}",
            exc_info=True,
        )
