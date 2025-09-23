# api/cache.py

import hashlib
import json
from typing import Dict, List, Any, Optional, TYPE_CHECKING, Union

from pydantic import BaseModel, Field, field_validator
from catalyst.resilience import invoke_with_resilience, MaxRetriesExceededError


if TYPE_CHECKING:
    from arq.connections import ArqRedis

from catalyst.utilities.logger import get_logger
from catalyst.clients import gemini as l0_gemini_client
from . import config as api_config
from . import prompts as api_prompts

logger = get_logger(__name__)


# Define the expected structure for the L0 key entities.
# The values can be a mix of types, so we use 'Any'.
class L0KeyEntities(BaseModel):
    # These fields are now guaranteed to be lists of strings or None.
    brand: Optional[List[str]] = None
    garment_type: Optional[List[str]] = None
    theme: Optional[List[str]] = None
    season: Optional[List[str]] = None
    region: Optional[List[str]] = None
    key_attributes: Optional[List[str]] = Field(default=[])
    year: Optional[List[Union[int, str]]] = None
    target_audience: Optional[str] = None

    # VALIDATOR 1: For fields that should be lists of strings.
    @field_validator(
        "brand",
        "garment_type",
        "theme",
        "season",
        "region",
        "key_attributes",
        mode="before",
    )
    @classmethod
    def _normalize_string_fields_to_list(cls, v: Any) -> Optional[List[str]]:
        """If a single string is passed, wrap it in a list."""
        if v is None:
            return None
        if isinstance(v, str):
            return [v] if v else None
        return v

    # VALIDATOR 2: A dedicated, more flexible validator just for the 'year' field.
    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year_to_list(cls, v: Any) -> Optional[List[Union[int, str]]]:
        """
        Accepts a single int, a single string, or a list, and ensures the
        output is always a list.
        """
        if v is None:
            return None
        # If it's a single item (int or string), wrap it in a list.
        if isinstance(v, (str, int)):
            return [v] if v else None
        # If it's already a list, pass it through.
        return v




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

        # Use .model_dump() with exclude_unset=True. This will correctly
        # omit any fields that were not explicitly set by the AI's response,
        # such as the default 'key_attributes=[]'.
        entities = entities_model.model_dump(exclude_unset=True)

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
