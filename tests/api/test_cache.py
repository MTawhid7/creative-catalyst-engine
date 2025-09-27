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

    # --- START: THE DEFINITIVE FIX ---
    # We must test the validators by using model_validate, which simulates
    # creating the model from raw data (like a JSON object).

    def test_string_fields_are_normalized_to_list(self):
        """Verify that single string values are wrapped in a list."""
        data = {"brand": "Chanel", "garment_type": "Jacket"}
        model = L0KeyEntities.model_validate(data)
        assert model.brand == ["Chanel"]
        assert model.garment_type == ["Jacket"]

    def test_year_field_is_normalized_to_list(self):
        """Verify that single int or string for 'year' is wrapped in a list."""
        model_int = L0KeyEntities.model_validate({"year": 2025})
        model_str = L0KeyEntities.model_validate({"year": "2025"})
        assert model_int.year == [2025]
        assert model_str.year == ["2025"]

    def test_lists_are_passed_through(self):
        """Verify that values that are already lists are not modified."""
        data = {"brand": ["Chanel", "Dior"], "year": [2025, 2026]}
        model = L0KeyEntities.model_validate(data)
        assert model.brand == ["Chanel", "Dior"]
        assert model.year == [2025, 2026]

    # --- END: THE DEFINITIVE FIX ---


@pytest.mark.asyncio
class TestGenerateDeterministicKey:
    """Unit tests for the _generate_deterministic_key function."""

    async def test_key_generation_success(self, mocker):
        """Verify a stable, sorted key is generated from a successful AI response."""
        # Arrange
        mock_response_model = L0KeyEntities.model_validate(
            {
                "theme": ["Cyberpunk"],
                "year": [2077, 2023],  # Unsorted
                "brand": "Arasaka",
            }
        )
        mocker.patch(
            "api.cache.invoke_with_resilience", return_value=mock_response_model
        )

        # Act
        result_key = await _generate_deterministic_key("test passage")

        # Assert
        expected_key = "brand:['Arasaka']|theme:['Cyberpunk']|year:['2023', '2077']"
        assert result_key == expected_key

    async def test_key_generation_handles_ai_failure(self, mocker):
        """Verify it returns None if the AI call fails."""
        mocker.patch(
            "api.cache.invoke_with_resilience",
            side_effect=MaxRetriesExceededError(ValueError("AI failed")),
        )
        result_key = await _generate_deterministic_key("test passage")
        assert result_key is None

    async def test_key_generation_handles_no_entities(self, mocker):
        """Verify it returns None if the AI returns an empty model."""
        mocker.patch("api.cache.invoke_with_resilience", return_value=L0KeyEntities())
        result_key = await _generate_deterministic_key("test passage")
        assert result_key is None


@pytest.mark.asyncio
class TestL0CacheFunctions:
    """Integration tests for the public get/set functions."""

    @pytest.fixture
    def mock_key_gen(self, mocker) -> AsyncMock:
        """Mocks the internal key generation function."""
        return mocker.patch(
            "api.cache._generate_deterministic_key", new_callable=AsyncMock
        )

    async def test_get_from_l0_cache_hit(self, mock_redis_client, mock_key_gen):
        """Verify a cache hit correctly retrieves and parses data."""
        mock_key_gen.return_value = "stable_key"
        cached_payload = {"report": "data"}
        mock_redis_client.get.return_value = json.dumps(cached_payload).encode("utf-8")

        result = await get_from_l0_cache("test", mock_redis_client)

        assert result == cached_payload
        expected_hash = hashlib.sha256("stable_key".encode()).hexdigest()
        mock_redis_client.get.assert_awaited_once_with(
            f"{api_config.L0_CACHE_PREFIX}:{expected_hash}"
        )

    async def test_get_from_l0_cache_miss(self, mock_redis_client, mock_key_gen):
        """Verify a cache miss returns None."""
        mock_key_gen.return_value = "stable_key"
        mock_redis_client.get.return_value = None
        result = await get_from_l0_cache("test", mock_redis_client)
        assert result is None

    async def test_set_in_l0_cache_success(self, mock_redis_client, mock_key_gen):
        """Verify a successful set operation calls redis with correct arguments."""
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
        """Verify redis.set is not called if key generation returns None."""
        mock_key_gen.return_value = None
        await set_in_l0_cache("test", {}, mock_redis_client)
        mock_redis_client.set.assert_not_called()
