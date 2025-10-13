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
    # This class remains unchanged as the model itself was not modified.
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
    """Unit tests for the seed-aware _generate_deterministic_key function."""

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_key_generation_success(self, seed: int, mocker):
        """Verify a stable, seed-aware key is generated."""
        mock_response_model = L0KeyEntities.model_validate(
            {"theme": ["Cyberpunk"], "year": [2077, 2023], "brand": "Arasaka"}
        )
        mocker.patch(
            "api.cache.invoke_with_resilience", return_value=mock_response_model
        )

        result_key = await _generate_deterministic_key("test passage", seed)

        base_key = "brand:['Arasaka']|theme:['Cyberpunk']|year:['2023', '2077']"
        expected_key = f"{base_key}|seed:{seed}"
        assert result_key == expected_key

    async def test_key_generation_handles_ai_failure(self, mocker):
        """Verify it returns None if the AI call fails."""
        mocker.patch(
            "api.cache.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        result_key = await _generate_deterministic_key("test passage", 0)
        assert result_key is None

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_key_generation_handles_no_entities(self, seed: int, mocker):
        """Verify it returns a seed-aware fallback hash."""
        mocker.patch("api.cache.invoke_with_resilience", return_value=L0KeyEntities())

        result_key = await _generate_deterministic_key("test passage", seed)

        expected_hash = hashlib.sha256("test passage".encode()).hexdigest()
        assert result_key == f"raw_passage_hash:{expected_hash}|seed:{seed}"


@pytest.mark.asyncio
class TestL0CacheFunctions:
    """Integration tests for the public get/set functions."""

    @pytest.fixture
    def mock_key_gen(self, mocker) -> AsyncMock:
        return mocker.patch(
            "api.cache._generate_deterministic_key", new_callable=AsyncMock
        )

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_get_from_l0_cache_hit(
        self, seed: int, mock_redis_client, mock_key_gen
    ):
        mock_key_gen.return_value = "stable_key"
        cached_payload = {"report": "data"}
        mock_redis_client.get.return_value = json.dumps(cached_payload).encode("utf-8")

        result = await get_from_l0_cache("test", seed, mock_redis_client)

        assert result == cached_payload
        mock_key_gen.assert_awaited_once_with("test", seed)

    @pytest.mark.parametrize("seed", [0, 5])
    async def test_set_in_l0_cache_success(
        self, seed: int, mock_redis_client, mock_key_gen
    ):
        mock_key_gen.return_value = "stable_key"
        payload = {"report": "data"}

        await set_in_l0_cache("test", seed, payload, mock_redis_client)

        mock_key_gen.assert_awaited_once_with("test", seed)
        expected_hash = hashlib.sha256("stable_key".encode()).hexdigest()
        mock_redis_client.set.assert_awaited_once_with(
            f"{api_config.L0_CACHE_PREFIX}:{expected_hash}",
            json.dumps(payload),
            ex=api_config.L0_CACHE_TTL_SECONDS,
        )
