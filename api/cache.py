# api/cache.py

"""
Service-Level L0 Cache Management. This version is async-native to work
seamlessly with the ARQ worker.
"""

import hashlib
import json
from typing import Dict, Any, Optional

from arq.connections import ArqRedis

# --- START: DEFINITIVE LOGGER FIX ---
# Replace the old Celery logger with our application's standard logger
# for consistent logging across the entire application.
from catalyst.utilities.logger import get_logger

# --- END: DEFINITIVE LOGGER FIX ---

from catalyst.clients import gemini as l0_gemini_client
from catalyst.utilities.json_parser import parse_json_from_llm_output
from . import config as api_config
from . import prompts as api_prompts

# Instantiate the logger using the application's standard utility.
logger = get_logger(__name__)


async def _generate_deterministic_key(user_passage: str) -> Optional[str]:
    """
    Makes a fast ASYNCHRONOUS AI call to extract core entities and builds a
    stable, deterministic key string from them.
    """
    try:
        prompt = api_prompts.L0_KEY_GENERATION_PROMPT.format(user_passage=user_passage)
        response = await l0_gemini_client.generate_content_async(prompt_parts=[prompt])

        if not response or "text" not in response:
            logger.warning("L0 key generation AI call returned no text content.")
            return None

        entities = parse_json_from_llm_output(response["text"])

        if not entities or not isinstance(entities, dict):
            logger.warning("L0 key generation did not extract a valid JSON object.")
            return None

        key_parts = []
        for key in sorted(entities.keys()):
            value = entities[key]
            if isinstance(value, list):
                key_parts.append(f"{key}:{sorted([str(v) for v in value])}")
            else:
                key_parts.append(f"{key}:{value}")

        stable_key = "|".join(key_parts)
        logger.info(f"Generated deterministic L0 key: '{stable_key}'")
        return stable_key

    except Exception as e:
        logger.error(f"❌ Failed to generate deterministic L0 key: {e}", exc_info=True)
        return None


async def get_from_l0_cache(
    user_passage: str, redis_client: ArqRedis
) -> Optional[Dict[str, Any]]:
    """Asynchronously checks the L0 cache for a result."""
    stable_key = await _generate_deterministic_key(user_passage)
    if not stable_key:
        return None

    try:
        key_hash = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
        cache_key = f"{api_config.L0_CACHE_PREFIX}:{key_hash}"

        cached_result = await redis_client.get(cache_key)

        if isinstance(cached_result, bytes):
            logger.warning(f"🎯 TRUE L0 CACHE HIT! for key: {cache_key}")
            return json.loads(cached_result.decode("utf-8"))

        logger.info(f"💨 True L0 Cache MISS for key: {cache_key}")
        return None

    except Exception as e:
        logger.error(f"⚠️ An error occurred during L0 cache check: {e}", exc_info=True)
        return None


async def set_in_l0_cache(
    user_passage: str, result: Dict[str, Any], redis_client: ArqRedis
):
    """Asynchronously stores a result in the L0 cache."""
    stable_key = await _generate_deterministic_key(user_passage)
    if not stable_key:
        logger.warning("Cannot set L0 cache because key generation failed.")
        return

    try:
        key_hash = hashlib.sha256(stable_key.encode("utf-8")).hexdigest()
        cache_key = f"{api_config.L0_CACHE_PREFIX}:{key_hash}"
        await redis_client.set(
            cache_key, json.dumps(result), ex=api_config.L0_CACHE_TTL_SECONDS
        )
        logger.info(f"✅ Stored new result in True L0 Cache with key: {cache_key}")
    except Exception as e:
        logger.error(f"⚠️ Failed to store result in L0 cache: {e}", exc_info=True)
