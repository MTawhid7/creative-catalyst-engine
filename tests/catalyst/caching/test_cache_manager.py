# tests/catalyst/caching/test_cache_manager.py

import pytest
from unittest.mock import AsyncMock

from catalyst.caching import cache_manager


# --- Unit Tests for the Semantic Key Generation ---


class TestCreateSemanticKey:
    """
    Unit tests for the internal _create_semantic_key function.
    Its output must be 100% deterministic.
    """

    @pytest.mark.parametrize(
        "brief, seed, expected_key",
        [
            (
                # Happy path: a full brief with seed 0
                {"theme_hint": "Cyberpunk Noir", "garment_type": ["Trench Coat"]},
                0,
                "garment_type: Trench Coat | theme_hint: Cyberpunk Noir | variation_seed: 0",
            ),
            (
                # Edge Case: Missing keys with a non-default seed
                {"theme_hint": "Aquatic Serenity", "season": "Spring/Summer"},
                5,
                "season: Spring/Summer | theme_hint: Aquatic Serenity | variation_seed: 5",
            ),
            (
                # Edge Case: Empty brief
                {},
                0,
                "variation_seed: 0",
            ),
        ],
    )
    def test_semantic_key_creation(self, brief, seed, expected_key):
        """Verify the semantic key is stable, sorted, and includes the seed."""
        # --- FIX: Pass the variation_seed to the function call ---
        assert cache_manager._create_semantic_key(brief, seed) == expected_key


# --- Integration Tests for the Cache Manager's Public Functions ---


@pytest.mark.asyncio
class TestCacheManagerIntegration:
    """
    Integration tests for the cache_manager's async functions.
    """

    async def test_check_report_cache_async(self, mocker):
        """
        Verify that check_report_cache_async generates a key with the seed
        and calls the report_cache.check method with it.
        """
        mock_brief = {"theme_hint": "Test Theme"}
        seed = 3
        expected_key = "theme_hint: Test Theme | variation_seed: 3"
        mock_check = mocker.patch(
            "catalyst.caching.cache_manager.report_cache.check",
            new_callable=AsyncMock,
            return_value="cached_payload",
        )

        # --- FIX: Pass the variation_seed ---
        result = await cache_manager.check_report_cache_async(mock_brief, seed)

        assert result == "cached_payload"
        mock_check.assert_awaited_once_with(expected_key)

    async def test_add_to_report_cache_async(self, mocker):
        """
        Verify that add_to_report_cache_async generates a key with the seed
        and calls report_cache.add with the correct key and payload.
        """
        mock_brief = {"theme_hint": "Test Theme"}
        mock_payload = {"data": "some_report_data"}
        seed = 1
        expected_key = "theme_hint: Test Theme | variation_seed: 1"
        mock_add = mocker.patch(
            "catalyst.caching.cache_manager.report_cache.add", new_callable=AsyncMock
        )

        # --- FIX: Pass the variation_seed ---
        await cache_manager.add_to_report_cache_async(mock_brief, mock_payload, seed)

        mock_add.assert_awaited_once_with(expected_key, mock_payload)
