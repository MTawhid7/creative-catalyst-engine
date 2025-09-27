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
        "brief, expected_key",
        [
            (
                # Happy path: a full, well-formed brief
                {
                    "theme_hint": "Cyberpunk Noir",
                    "garment_type": ["Trench Coat", "Boots"],
                    "brand_category": "Streetwear",
                    "target_audience": "Tech enthusiasts",
                    "region": "Neo-Tokyo",
                    "key_attributes": ["Reflective", "Asymmetrical"],
                    "season": "Fall/Winter",
                    "year": [2077],
                },
                "brand_category: Streetwear | garment_type: Boots, Trench Coat | key_attributes: Asymmetrical, Reflective | region: Neo-Tokyo | season: Fall/Winter | target_audience: Tech enthusiasts | theme_hint: Cyberpunk Noir | year: 2077",
            ),
            (
                # Edge Case: Missing some keys
                {
                    "theme_hint": "Aquatic Serenity",
                    "garment_type": ["Flowing Gown"],
                    "season": "Spring/Summer",
                },
                "garment_type: Flowing Gown | season: Spring/Summer | theme_hint: Aquatic Serenity",
            ),
            (
                # Edge Case: Mixed types in a list (int and str)
                {
                    "theme_hint": "Temporal Fusion",
                    "year": [2025, "2026"],
                },
                "theme_hint: Temporal Fusion | year: 2025, 2026",
            ),
            (
                # Edge Case: Empty brief
                {},
                "",
            ),
        ],
    )
    def test_semantic_key_creation(self, brief, expected_key):
        """Verify that the semantic key is stable, sorted, and handles various inputs."""
        assert cache_manager._create_semantic_key(brief) == expected_key


# --- Integration Tests for the Cache Manager's Public Functions ---


@pytest.mark.asyncio
class TestCacheManagerIntegration:
    """
    Integration tests for the cache_manager's async functions.
    These tests mock the lower-level report_cache module to isolate the manager.
    """

    async def test_check_report_cache_async(self, mocker):
        """
        Verify that check_report_cache_async generates a key and calls the
        report_cache.check method with it.
        """
        # Arrange
        mock_brief = {"theme_hint": "Test Theme"}
        expected_key = "theme_hint: Test Theme"

        # Mock the dependency
        mock_check = mocker.patch(
            "catalyst.caching.cache_manager.report_cache.check",
            new_callable=AsyncMock,
            return_value="cached_payload",
        )

        # Act
        result = await cache_manager.check_report_cache_async(mock_brief)

        # Assert
        assert result == "cached_payload"
        mock_check.assert_awaited_once_with(expected_key)

    async def test_add_to_report_cache_async(self, mocker):
        """
        Verify that add_to_report_cache_async generates a key and calls the
        report_cache.add method with the correct key and payload.
        """
        # Arrange
        mock_brief = {"theme_hint": "Test Theme"}
        mock_payload = {"data": "some_report_data"}
        expected_key = "theme_hint: Test Theme"

        # Mock the dependency
        mock_add = mocker.patch(
            "catalyst.caching.cache_manager.report_cache.add", new_callable=AsyncMock
        )

        # Act
        await cache_manager.add_to_report_cache_async(mock_brief, mock_payload)

        # Assert
        mock_add.assert_awaited_once_with(expected_key, mock_payload)
