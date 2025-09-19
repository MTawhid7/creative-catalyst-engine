# api/cache.py

import hashlib
import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Union

# --- START: RESILIENCE REFACTOR ---
from pydantic import BaseModel, Field
from catalyst.resilience import invoke_with_resilience, MaxRetriesExceededError

# --- END: RESILIENCE REFACTOR ---

if TYPE_CHECKING:
    from arq.connections import ArqRedis

from catalyst.utilities.logger import get_logger
from catalyst.clients import gemini as l0_gemini_client
from . import config as api_config
from . import prompts as api_prompts

logger = get_logger(__name__)


# --- START: RESILIENCE REFACTOR (New Model) ---
# Define the expected structure for the L0 key entities.
# The values can be a mix of types, so we use 'Any'.
class L0KeyEntities(BaseModel):
    brand: Optional[Union[str, List[str]]] = None
    garment_type: Optional[Union[str, List[str]]] = None
    theme: Optional[Union[str, List[str]]] = None
    season: Optional[str] = None
    year: Optional[Union[int, str, List[Union[int, str]]]] = None
    target_audience: Optional[str] = None
    region: Optional[Union[str, List[str]]] = None
    key_attributes: Optional[List[str]] = Field(default=[])


# --- END: RESILIENCE REFACTOR (New Model) ---


async def _generate_deterministic_key(user_passage: str) -> Optional[str]:
    """
    Makes a fast, RESILIENT AI call to extract core entities and builds a
    stable, deterministic key string from them.
    """
    try:
        prompt = api_prompts.L0_KEY_GENERATION_PROMPT.format(user_passage=user_passage)

        entities_model = await invoke_with_resilience(
            ai_function=l0_gemini_client.generate_content_async,
            prompt=prompt,
            response_schema=L0KeyEntities,
        )

        # --- START: THE DEFINITIVE FIX ---
        # Use .model_dump() with exclude_unset=True. This will correctly
        # omit any fields that were not explicitly set by the AI's response,
        # such as the default 'key_attributes=[]'.
        entities = entities_model.model_dump(exclude_unset=True)
        # --- END: THE DEFINITIVE FIX ---

        if not entities:
            logger.warning("L0 key generation did not extract any entities.")
            return None

        key_parts = []
        for key in sorted(entities.keys()):
            value = entities[key]
            if isinstance(value, list):
                # Use str() to handle mixed types like int/str in year
                key_parts.append(f"{key}:{sorted([str(v) for v in value])}")
            else:
                key_parts.append(f"{key}:{value}")

        stable_key = "|".join(key_parts)
        logger.info(f"Generated deterministic L0 key: '{stable_key}'")
        return stable_key

    except MaxRetriesExceededError:
        logger.error("❌ Failed to generate deterministic L0 key after all retries.")
        return None
    except Exception as e:
        logger.error(
            f"❌ An unexpected error occurred during L0 key generation: {e}",
            exc_info=True,
        )
        return None


async def get_from_l0_cache(
    user_passage: str, redis_client: "ArqRedis"
) -> Optional[Dict[str, Any]]:
    # ... (this function is unchanged)
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
    user_passage: str, result: Dict[str, Any], redis_client: "ArqRedis"
):
    # ... (this function is unchanged)
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
