# tests/catalyst/caching/test_cache_manager.py

import pytest
from unittest.mock import AsyncMock
from pathlib import Path

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

        result = await cache_manager.check_report_cache_async(mock_brief, seed)

        assert result == "cached_payload"
        mock_check.assert_awaited_once_with(expected_key)

    async def test_add_to_report_cache_async(self, mocker):
        """
        Verify that add_to_report_cache_async now correctly orchestrates
        copying artifacts and adding to the semantic cache.
        """
        # Arrange
        mock_brief = {"theme_hint": "Test Theme"}
        mock_report = {"final_report": "some_data"}
        seed = 1
        dummy_path = Path("/tmp/dummy_artifacts")

        mock_add = mocker.patch(
            "catalyst.caching.cache_manager.report_cache.add", new_callable=AsyncMock
        )
        mock_copy = mocker.patch("catalyst.caching.cache_manager.shutil.copytree")

        # Act: Call the function with all required arguments
        await cache_manager.add_to_report_cache_async(
            brief=mock_brief,
            final_report=mock_report,
            variation_seed=seed,
            source_artifact_path=dummy_path,
        )

        # Assert
        mock_copy.assert_called_once()
        mock_add.assert_awaited_once()

        # Verify the payload passed to the underlying cache module is correct
        call_args = mock_add.call_args[0]
        semantic_key = call_args[0]
        payload_to_cache = call_args[1]

        assert semantic_key == "theme_hint: Test Theme | variation_seed: 1"
        assert payload_to_cache["final_report"] == mock_report
        assert "cached_results_path" in payload_to_cache
