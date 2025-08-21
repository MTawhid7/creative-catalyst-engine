"""
The Discovery Engine: The Research Librarian for the Creative Catalyst Engine.
(Upgraded version with multi-vector query generation and full source utilization)
"""

import asyncio
import random
import requests
from typing import List, Dict, Optional, Any

from .. import settings
from ..utilities.logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

EXCLUDED_DOMAINS = [
    "youtube.com",
    "vimeo.com",
    "tiktok.com",
    "pinterest.com",
    "linkedin.com",
    "amazon.com",
    "facebook.com",
    "reddit.com",
    "aliexpress.com",
]


def _sync_google_search(query: str) -> Optional[List[str]]:
    """
    Performs a synchronous Google Custom Search API call using the robust 'requests' library.
    """
    logger.info(f"Executing search query: '{query}'")
    params = {
        "key": settings.GOOGLE_API_KEY,
        "cx": settings.SEARCH_ENGINE_ID,
        "q": query,
        "num": settings.SEARCH_NUM_RESULTS,
    }
    try:
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1", params=params, timeout=10
        )
        response.raise_for_status()
        results = response.json()
        return [
            item.get("link", "")
            for item in results.get("items", [])
            if item.get("link")
        ]
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error during Google search for '{query}'", exc_info=True)
        return None
    except Exception as e:
        logger.error(
            f"Error parsing Google search results for '{query}'", exc_info=True
        )
        return None


# --- START OF NEW HELPER FUNCTION ---
def _load_all_sources(region: Optional[str]) -> Dict[str, List[str]]:
    """
    Loads and flattens all relevant source lists from the sources.yaml config.
    """
    config = settings.SOURCES_CONFIG
    sources: Dict[str, List[str]] = {
        "global_authorities": config.get("market_pulse", {}).get(
            "global_authorities", []
        ),
        "fashion_weeks": config.get("market_pulse", {}).get("fashion_weeks", []),
        "visual_platforms": config.get("market_pulse", {}).get("visual_platforms", []),
        "youth_culture_media": config.get("market_pulse", {}).get(
            "youth_culture_media", []
        ),
        "abstract_concepts": config.get("cultural_deep_dive", {}).get(
            "abstract_concepts", []
        ),
        "archives_and_museums": config.get("cultural_deep_dive", {}).get(
            "archives_and_museums", []
        ),
        "forecasting_agencies": config.get("commercial_intelligence", {}).get(
            "forecasting_agencies", []
        ),
    }

    # Add regional authorities if a region is specified
    if region:
        regional_authorities = (
            config.get("market_pulse", {})
            .get("regional_authorities", {})
            .get(region, [])
        )
        sources["global_authorities"].extend(regional_authorities)

    return sources


# --- END OF NEW HELPER FUNCTION ---


def _generate_queries_from_brief(brief: Dict) -> List[str]:
    """
    Creates a sophisticated, multi-vector list of search queries by decomposing
    the enriched brief and systematically using all configured sources.
    """
    logger.info("Generating decomposed multi-vector search queries...")
    theme_hint = brief.get("theme_hint", "")
    season = brief.get("season", "")
    year = brief.get("year", "")
    search_keywords = brief.get("search_keywords", [])
    if theme_hint not in search_keywords:
        search_keywords.insert(0, theme_hint)

    sources = _load_all_sources(brief.get("region"))
    queries = set()

    # --- START OF CHANGE ---
    # The f-strings have been modified to remove the double quotes around the
    # theme_hint and keyword variables for a broader, more flexible search.
    # Quotes around the 'source' variable are kept to ensure exact matches
    # for multi-word publication names (e.g., "Business of Fashion").

    # STRATEGY 1: High-Precision Queries
    high_value_sources = sources["global_authorities"] + sources["forecasting_agencies"]
    if high_value_sources:
        for keyword in random.sample(search_keywords, min(len(search_keywords), 2)):
            for source in random.sample(
                high_value_sources, min(len(high_value_sources), 2)
            ):
                queries.add(f'{keyword} "{source}" {season} trend report')

    # STRATEGY 2: Visual & Youth Culture Queries
    visual_sources = sources["visual_platforms"] + sources["youth_culture_media"]
    if visual_sources:
        for source in random.sample(visual_sources, min(len(visual_sources), 3)):
            queries.add(f'{theme_hint} "{source}" aesthetic')

    # STRATEGY 3: Deep Dive & Inspirational Queries
    inspirational_sources = (
        sources["abstract_concepts"] + sources["archives_and_museums"]
    )
    if inspirational_sources:
        for source in random.sample(
            inspirational_sources, min(len(inspirational_sources), 3)
        ):
            queries.add(f'{theme_hint} inspiration from "{source}"')

    # STRATEGY 4: Speculative Future-Dated Queries
    if year and season:
        queries.add(f"{theme_hint} trend forecast {season} {year}")
        queries.add(f"fashion trend report {season} {year} filetype:pdf")

    # --- END OF CHANGE ---

    final_queries = list(queries)
    if len(final_queries) > settings.MAX_QUERIES:
        final_queries = random.sample(final_queries, settings.MAX_QUERIES)

    logger.info(f"Generated {len(final_queries)} targeted, multi-vector queries.")
    return final_queries


async def discover_urls_async(brief: Dict) -> List[str]:
    """
    The main public function that orchestrates the URL discovery process.
    """
    logger.info("Starting the URL discovery process...")

    queries = _generate_queries_from_brief(brief)
    if not queries:
        logger.warning("No search queries were generated from the brief.")
        return []

    search_tasks = [asyncio.to_thread(_sync_google_search, q) for q in queries]
    results_list = await asyncio.gather(*search_tasks)

    all_urls = {
        url
        for url_list in results_list
        if url_list
        for url in url_list
        if not any(domain in url for domain in EXCLUDED_DOMAINS)
    }

    logger.info(f"Discovered {len(all_urls)} unique, usable URLs for analysis.")
    return list(all_urls)
