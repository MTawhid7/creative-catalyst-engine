# tests/catalyst/caching/test_cache_manager.py

import pytest
from unittest.mock import AsyncMock

# Import the module we are testing
from catalyst.caching import cache_manager

# Define the full path to the module we need to mock
REPORT_CACHE_MOCK_PATH = "catalyst.caching.cache_manager.report_cache"


@pytest.fixture
def mock_brief():
    """Provides a consistent, sample enriched_brief dictionary for testing."""
    return {
        "theme_hint": "Cyberpunk Formalwear",
        "garment_type": "Blazer",
        "season": "Fall/Winter",
        "year": 2025,
        "key_attributes": ["Tailored", "Asymmetric"],
        # This field should be ignored by the key generator
        "desired_mood": ["Dark", "Sophisticated"],
    }


@pytest.mark.asyncio
async def test_check_report_cache_hit(mocker, mock_brief):
    """
    Tests that if the underlying report_cache finds a document,
    the cache_manager returns it.
    """
    # ARRANGE
    # Mock the entire report_cache module.
    mock_report_cache = mocker.patch(REPORT_CACHE_MOCK_PATH)
    mock_report_cache.check = AsyncMock(return_value='{"report": "found"}')

    # ACT
    result = await cache_manager.check_report_cache_async(mock_brief)

    # ASSERT
    # 1. Assert that the underlying check function was called.
    mock_report_cache.check.assert_called_once()
    # 2. Assert that the result from the cache was returned.
    assert result == '{"report": "found"}'


@pytest.mark.asyncio
async def test_check_report_cache_miss(mocker, mock_brief):
    """
    Tests that if the underlying report_cache returns None,
    the cache_manager also returns None.
    """
    # ARRANGE
    mock_report_cache = mocker.patch(REPORT_CACHE_MOCK_PATH)
    mock_report_cache.check = AsyncMock(return_value=None)

    # ACT
    result = await cache_manager.check_report_cache_async(mock_brief)

    # ASSERT
    mock_report_cache.check.assert_called_once()
    assert result is None


@pytest.mark.asyncio
async def test_add_to_report_cache(mocker, mock_brief):
    """
    Tests that add_to_report_cache_async correctly calls the underlying
    report_cache.add function with the right key and payload.
    """
    # ARRANGE
    mock_report_cache = mocker.patch(REPORT_CACHE_MOCK_PATH)
    mock_report_cache.add = AsyncMock()

    payload = {"final_report": "some data"}

    # ACT
    await cache_manager.add_to_report_cache_async(mock_brief, payload)

    # ASSERT
    # 1. Assert that the underlying add function was called.
    mock_report_cache.add.assert_called_once()
    # 2. Check the arguments it was called with.
    args, kwargs = mock_report_cache.add.call_args

    # The first argument should be the generated semantic key
    expected_key = "garment_type: Blazer | key_attributes: Asymmetric, Tailored | season: Fall/Winter | theme_hint: Cyberpunk Formalwear | year: 2025"
    assert args[0] == expected_key

    # The second argument should be the payload
    assert args[1] == payload


def test_create_semantic_key_is_deterministic(mock_brief):
    """
    Unit tests the _create_semantic_key helper to ensure it's deterministic,
    meaning the order of keys in the input dictionary does not affect the output.
    """
    # ARRANGE
    # Create a second brief with the same data but a different key order.
    brief_shuffled = {
        "season": "Fall/Winter",
        "year": 2025,
        "garment_type": "Blazer",
        "key_attributes": ["Tailored", "Asymmetric"],
        "theme_hint": "Cyberpunk Formalwear",
    }

    # ACT
    key1 = cache_manager._create_semantic_key(mock_brief)
    key2 = cache_manager._create_semantic_key(brief_shuffled)

    # ASSERT
    # The keys must be identical, proving the sorting logic works.
    assert key1 == key2
    assert (
        "desired_mood" not in key1
    )  # Also ensure non-deterministic keys are excluded.
