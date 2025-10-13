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


# L0KeyEntities model remains the same...
class L0KeyEntities(BaseModel):
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
        if v is None:
            return None
        if isinstance(v, str):
            return [v] if v else None
        return v

    # VALIDATOR 2: A dedicated, more flexible validator just for the 'year' field.
    @field_validator("year", mode="before")
    @classmethod
    def _normalize_year_to_list(cls, v: Any) -> Optional[List[Union[int, str]]]:
        if v is None:
            return None
        if isinstance(v, (str, int)):
            return [v] if v else None
        return v


# --- CHANGE: Update the function to accept the variation_seed ---
async def _generate_deterministic_key(
    user_passage: str, variation_seed: int
) -> Optional[str]:
    try:
        prompt = api_prompts.L0_KEY_GENERATION_PROMPT.format(user_passage=user_passage)
        entities_model = await invoke_with_resilience(
            ai_function=l0_gemini_client.generate_content_async,
            prompt=prompt,
            response_schema=L0KeyEntities,
        )
        entities = entities_model.model_dump(exclude_unset=True)

        if not entities:
            normalized_passage = user_passage.strip().lower()
            raw_hash = hashlib.sha256(normalized_passage.encode()).hexdigest()
            # --- ADD: Include the seed in the fallback key as well ---
            return f"raw_passage_hash:{raw_hash}|seed:{variation_seed}"

        key_parts = []
        for key in sorted(entities.keys()):
            value = entities[key]
            if isinstance(value, list):
                key_parts.append(f"{key}:{sorted([str(v) for v in value])}")
            else:
                key_parts.append(f"{key}:{value}")

        stable_key = "|".join(key_parts)

        # --- ADD: Append the variation seed to the stable key to make it unique ---
        stable_key_with_seed = f"{stable_key}|seed:{variation_seed}"

        logger.info(f"Generated deterministic L0 key: '{stable_key_with_seed}'")
        return stable_key_with_seed

    except MaxRetriesExceededError:
        logger.error("❌ Failed to generate deterministic L0 key after all retries.")
        return None
    except Exception as e:
        logger.error(
            f"❌ An unexpected error occurred during L0 key generation: {e}",
            exc_info=True,
        )
        return None


# --- CHANGE: Update cache functions to accept and use the variation_seed ---
async def get_from_l0_cache(
    user_passage: str, variation_seed: int, redis_client: "ArqRedis"
) -> Optional[Dict[str, Any]]:
    stable_key = await _generate_deterministic_key(user_passage, variation_seed)
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
    user_passage: str,
    variation_seed: int,
    result: Dict[str, Any],
    redis_client: "ArqRedis",
):
    stable_key = await _generate_deterministic_key(user_passage, variation_seed)
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
