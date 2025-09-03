# api/cache.py

"""
Service-Level L0 Cache Management.

This module implements the "True L0" cache, which sits in front of the
entire creative pipeline. It is designed to provide a high-speed,
exact-match cache for the user's *intent*, even when the raw input
string varies due to upstream generation.
"""

import asyncio
import hashlib
import json
from typing import Dict, Any, Optional

from celery.utils.log import get_task_logger
from redis import Redis

from catalyst.clients import gemini_client as l0_gemini_client

logger = get_task_logger(__name__)

# --- L0 Cache Configuration ---
L0_CACHE_PREFIX = "l0_cache:intent"
L0_CACHE_TTL_SECONDS = 60 * 60 * 24  # 24 hours

# --- L0 Key Generation Prompt ---
L0_KEY_GENERATION_PROMPT = """
You are a highly efficient entity extraction bot. Your ONLY function is to extract a specific set of key-value pairs from the user's text.

**CRITICAL RULES:**
- You MUST extract values for the following keys if they are present in the text: `brand`, `garment_type`, `theme`, `season`, `year`, `target_audience`, `region`, `key_attributes`.
- If a value is not present in the text, you MUST omit the key from the JSON output. DO NOT infer or invent values.
- For `key_attributes`, return a list of strings if multiple are found.
- Your response MUST be a valid JSON object and nothing else.

---
**EXAMPLE 1 (Complex Request)**
USER TEXT: "Generate a trend report on the iconic Chanel tweed jacket for Spring/Summer 2026, reimagined for a modern, professional woman in Europe."
JSON OUTPUT:
{{
  "brand": "Chanel",
  "garment_type": "tweed jacket",
  "season": "Spring/Summer",
  "year": 2026,
  "target_audience": "modern professional woman",
  "region": "Europe"
}}
---
**EXAMPLE 2 (Attribute-heavy Request)**
USER TEXT: "A report on minimalist and functional outerwear."
JSON OUTPUT:
{{
  "garment_type": "outerwear",
  "key_attributes": ["minimalist", "functional"]
}}
---
**EXAMPLE 3 (Theme-only Request)**
USER TEXT: "gorpcore trend report"
JSON OUTPUT:
{{
  "theme": "gorpcore"
}}
---
USER TEXT: "{user_passage}"
JSON OUTPUT:
"""


def _generate_deterministic_key(user_passage: str) -> Optional[str]:
    """
    Makes a fast AI call to extract core entities and builds a stable,
    deterministic key string from them. This function is synchronous but
    calls an async function internally.
    """
    try:
        prompt = L0_KEY_GENERATION_PROMPT.format(user_passage=user_passage)

        response = asyncio.run(
            l0_gemini_client.generate_content_async(prompt_parts=[prompt])
        )

        if not response or not isinstance(response, dict):
            logger.warning(
                "L0 key generation AI call returned no response or invalid type."
            )
            return None

        entities = response
        if not entities:
            logger.info(
                "L0 key generation did not extract any entities. Cannot create key."
            )
            return None

        key_parts = []
        for key in sorted(entities.keys()):
            value = entities[key]
            if isinstance(value, list):
                key_parts.append(f"{key}:{sorted(value)}")
            else:
                key_parts.append(f"{key}:{value}")

        stable_key = "|".join(key_parts)
        logger.info(f"Generated deterministic L0 key: '{stable_key}'")
        return stable_key

    except Exception as e:
        logger.error(f"❌ Failed to generate deterministic L0 key: {e}", exc_info=True)
        return None


def get_from_l0_cache(
    user_passage: str, redis_client: Redis
) -> Optional[Dict[str, Any]]:
    """
    Checks the L0 cache for a result using a deterministically generated key.
    This is a synchronous function.
    """
    stable_key = _generate_deterministic_key(user_passage)
    if not stable_key:
        return None

    try:
        key_hash = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
        cache_key = f"{L0_CACHE_PREFIX}:{key_hash}"

        cached_result = redis_client.get(cache_key)

        # --- START OF FINAL FIX ---
        # The redis `get` method returns bytes or None. This single, explicit
        # check satisfies the static analyzer and is robust at runtime.
        if isinstance(cached_result, bytes):
            logger.warning(
                f"🎯 TRUE L0 CACHE HIT! Returning stored result for key: {cache_key}"
            )
            return json.loads(cached_result.decode("utf-8"))
        # --- END OF FINAL FIX ---

        logger.info(f"💨 True L0 Cache MISS for key: {cache_key}")
        return None

    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)
        return None


def set_in_l0_cache(user_passage: str, result: Dict[str, Any], redis_client: Redis):
    """
    Stores a result in the L0 cache using a deterministically generated key.
    This is a synchronous function.
    """
    stable_key = _generate_deterministic_key(user_passage)
    if not stable_key:
        logger.warning("Cannot set L0 cache because key generation failed.")
        return

    try:
        key_hash = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
        cache_key = f"{L0_CACHE_PREFIX}:{key_hash}"

        redis_client.set(cache_key, json.dumps(result), ex=L0_CACHE_TTL_SECONDS)

        logger.info(f"✅ Stored new result in True L0 Cache with key: {cache_key}")

    except Exception as e:
        logger.error(f"⚠️ Failed to store result in L0 cache: {e}", exc_info=True)
