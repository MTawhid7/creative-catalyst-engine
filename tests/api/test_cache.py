# tests/api/test_cache.py

import pytest
import json
import hashlib
from unittest.mock import AsyncMock

from api.cache import (
    L0KeyEntities,
    _generate_deterministic_key,
    get_from_l0_cache,
    set_in_l0_cache,
)
from api import config as api_config
from catalyst.resilience import MaxRetriesExceededError


@pytest.fixture
def mock_redis_client() -> AsyncMock:
    """Provides a mock ARQ Redis client."""
    return AsyncMock()


class TestL0KeyEntitiesModel:
    """Unit tests for the Pydantic model and its validators."""

    def test_string_fields_are_normalized_to_list(self):
        data = {"brand": "Chanel", "garment_type": "Jacket"}
        model = L0KeyEntities.model_validate(data)
        assert model.brand == ["Chanel"]
        assert model.garment_type == ["Jacket"]

    def test_year_field_is_normalized_to_list(self):
        model_int = L0KeyEntities.model_validate({"year": 2025})
        assert model_int.year == [2025]

    def test_lists_are_passed_through(self):
        data = {"brand": ["Chanel", "Dior"], "year": [2025, 2026]}
        model = L0KeyEntities.model_validate(data)
        assert model.brand == ["Chanel", "Dior"]
        assert model.year == [2025, 2026]


@pytest.mark.asyncio
class TestGenerateDeterministicKey:
    """Unit tests for the _generate_deterministic_key function."""

    async def test_key_generation_success(self, mocker):
        mock_response_model = L0KeyEntities.model_validate(
            {"theme": ["Cyberpunk"], "year": [2077, 2023], "brand": "Arasaka"}
        )
        mocker.patch(
            "api.cache.invoke_with_resilience", return_value=mock_response_model
        )
        result_key = await _generate_deterministic_key("test passage")
        expected_key = "brand:['Arasaka']|theme:['Cyberpunk']|year:['2023', '2077']"
        assert result_key == expected_key

    async def test_key_generation_handles_ai_failure(self, mocker):
        mocker.patch(
            "api.cache.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        result_key = await _generate_deterministic_key("test passage")
        assert result_key is None

    async def test_key_generation_handles_no_entities(self, mocker):
        """Verify it returns a fallback hash if the AI returns an empty model."""
        mocker.patch("api.cache.invoke_with_resilience", return_value=L0KeyEntities())

        # --- CHANGE: Assert the new fallback behavior instead of None ---
        result_key = await _generate_deterministic_key("test passage")
        expected_hash = hashlib.sha256("test passage".encode()).hexdigest()
        assert result_key == f"raw_passage_hash:{expected_hash}"


@pytest.mark.asyncio
class TestL0CacheFunctions:
    """Integration tests for the public get/set functions."""

    @pytest.fixture
    def mock_key_gen(self, mocker) -> AsyncMock:
        return mocker.patch(
            "api.cache._generate_deterministic_key", new_callable=AsyncMock
        )

    async def test_get_from_l0_cache_hit(self, mock_redis_client, mock_key_gen):
        mock_key_gen.return_value = "stable_key"
        cached_payload = {"report": "data"}
        mock_redis_client.get.return_value = json.dumps(cached_payload).encode("utf-8")
        result = await get_from_l0_cache("test", mock_redis_client)
        assert result == cached_payload

    async def test_get_from_l0_cache_miss(self, mock_redis_client, mock_key_gen):
        mock_key_gen.return_value = "stable_key"
        mock_redis_client.get.return_value = None
        result = await get_from_l0_cache("test", mock_redis_client)
        assert result is None

    async def test_set_in_l0_cache_success(self, mock_redis_client, mock_key_gen):
        mock_key_gen.return_value = "stable_key"
        payload = {"report": "data"}
        await set_in_l0_cache("test", payload, mock_redis_client)
        expected_hash = hashlib.sha256("stable_key".encode()).hexdigest()
        mock_redis_client.set.assert_awaited_once_with(
            f"{api_config.L0_CACHE_PREFIX}:{expected_hash}",
            json.dumps(payload),
            ex=api_config.L0_CACHE_TTL_SECONDS,
        )

    async def test_set_in_l0_cache_skips_if_key_gen_fails(
        self, mock_redis_client, mock_key_gen
    ):
        mock_key_gen.return_value = None
        await set_in_l0_cache("test", {}, mock_redis_client)
        mock_redis_client.set.assert_not_called()
