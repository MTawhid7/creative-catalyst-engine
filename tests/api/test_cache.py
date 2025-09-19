# tests/api/test_cache.py

import pytest
from unittest.mock import AsyncMock, patch

# Import the functions and models we are testing
from api.cache import (
    _generate_deterministic_key,
    get_from_l0_cache,
    L0KeyEntities,
)
from catalyst.resilience import MaxRetriesExceededError

# Define the path to the function we need to mock
INVOKER_PATH = "api.cache.invoke_with_resilience"


@pytest.mark.asyncio
async def test_generate_deterministic_key_happy_path(mocker):
    """
    Tests that the function correctly sorts keys and creates a stable string
    from a standard AI response.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    # Note the unsorted order here
    mock_entities = L0KeyEntities(
        theme="futurism", brand="Chanel", garment_type="jacket"
    )
    mock_invoker.return_value = mock_entities

    # ACT
    result_key = await _generate_deterministic_key("a user prompt")

    # ASSERT
    # The key should be alphabetically sorted by key name.
    expected_key = "brand:Chanel|garment_type:jacket|theme:futurism"
    assert result_key == expected_key


@pytest.mark.asyncio
async def test_generate_deterministic_key_handles_lists(mocker):
    """
    Tests that the function correctly sorts the items *within* a list to
    ensure the final key is deterministic.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    # Note the unsorted list
    mock_entities = L0KeyEntities(key_attributes=["leather", "zippers", "asymmetric"])
    mock_invoker.return_value = mock_entities

    # ACT
    result_key = await _generate_deterministic_key("a user prompt")

    # ASSERT
    # The list items should be sorted alphabetically.
    expected_key = "key_attributes:['asymmetric', 'leather', 'zippers']"
    assert result_key == expected_key


@pytest.mark.asyncio
async def test_generate_deterministic_key_handles_ai_failure(mocker):
    """
    Tests that if the AI call fails, the function gracefully returns None.
    """
    # ARRANGE
    mock_invoker = mocker.patch(INVOKER_PATH)
    mock_invoker.side_effect = MaxRetriesExceededError(
        last_exception=ValueError("AI failed")
    )

    # ACT
    result_key = await _generate_deterministic_key("a user prompt")

    # ASSERT
    assert result_key is None


@pytest.mark.asyncio
async def test_get_from_l0_cache_stops_if_key_gen_fails(mocker):
    """
    Tests the safety check in the wrapper: if key generation returns None,
    we should not proceed to query Redis.
    """
    # ARRANGE
    # Mock the key generation function directly to force a failure
    mocker.patch("api.cache._generate_deterministic_key", return_value=None)
    mock_redis_client = AsyncMock()

    # ACT
    result = await get_from_l0_cache("any prompt", mock_redis_client)

    # ASSERT
    assert result is None
    # The most important assertion: Redis was never touched.
    mock_redis_client.get.assert_not_called()
