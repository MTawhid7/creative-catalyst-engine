# tests/catalyst/caching/test_report_cache.py

import pytest
from unittest.mock import MagicMock, AsyncMock
import importlib  # <-- Import the importlib library

# Import the module we are testing
from catalyst.caching import report_cache

# Define paths to the clients we need to mock
GEMINI_EMBEDDING_PATH = "catalyst.caching.report_cache.gemini.generate_embedding_async"
CHROMADB_CLIENT_PATH = "catalyst.caching.report_cache.chromadb.HttpClient"
CACHE_SETTINGS_PATH = "catalyst.caching.report_cache.settings"


@pytest.fixture(autouse=True)
def mock_clients(mocker):
    """
    This autouse fixture mocks the external clients and then reloads the
    report_cache module to ensure it initializes with the mocks in place.
    """
    mock_gemini = mocker.patch(GEMINI_EMBEDDING_PATH, return_value=[0.1, 0.2, 0.3])

    mock_chroma_collection = MagicMock()
    mock_chroma_client = mocker.patch(CHROMADB_CLIENT_PATH)
    mock_chroma_client.return_value.get_or_create_collection.return_value = (
        mock_chroma_collection
    )

    mock_settings = mocker.patch(CACHE_SETTINGS_PATH)
    mock_settings.CACHE_DISTANCE_THRESHOLD = 0.15

    # --- START: THE CRITICAL FIX ---
    # Reload the module under test. This forces its module-level code
    # (like the ChromaDB client initialization) to re-run using our mocks.
    importlib.reload(report_cache)
    # --- END: THE CRITICAL FIX ---

    return mock_gemini, mock_chroma_collection


@pytest.mark.asyncio
async def test_check_cache_hit_when_distance_is_low(mock_clients):
    """
    Tests a successful cache hit when a similar document is found
    below the distance threshold.
    """
    # ARRANGE
    _, mock_collection = mock_clients

    # --- START: THE FIX ---
    # We change the mock distance to be clearly *less than* the default 0.10 threshold.
    # This correctly tests the "<" logic in the application.
    mock_collection.query.return_value = {
        "documents": [["cached_payload"]],
        "distances": [[0.09]],
    }
    # --- END: THE FIX ---

    # ACT
    result = await report_cache.check("test key")

    # ASSERT
    assert result == "cached_payload"
    mock_collection.query.assert_called_once()


@pytest.mark.asyncio
async def test_check_cache_miss_when_distance_is_high(mock_clients):
    """
    Tests a cache miss when the closest document is still above
    the distance threshold.
    """
    # ARRANGE
    _, mock_collection = mock_clients
    mock_collection.query.return_value = {
        "documents": [["some_other_payload"]],
        "distances": [[0.2]],
    }

    # ACT
    result = await report_cache.check("test key")

    # ASSERT
    assert result is None
    mock_collection.query.assert_called_once()


@pytest.mark.asyncio
async def test_check_cache_miss_when_no_documents_found(mock_clients):
    """
    Tests a cache miss when the query returns no results.
    """
    # ARRANGE
    _, mock_collection = mock_clients
    mock_collection.query.return_value = {"documents": [[]], "distances": [[]]}

    # ACT
    result = await report_cache.check("test key")

    # ASSERT
    assert result is None


@pytest.mark.asyncio
async def test_check_returns_none_if_embedding_fails(mock_clients):
    """
    Tests that if the Gemini embedding call fails, the cache check
    returns None gracefully.
    """
    # ARRANGE
    mock_gemini, mock_collection = mock_clients
    mock_gemini.return_value = None

    # ACT
    result = await report_cache.check("test key")

    # ASSERT
    assert result is None
    mock_collection.query.assert_not_called()


@pytest.mark.asyncio
async def test_add_to_cache_success(mock_clients):
    """
    Tests that the 'add' function correctly generates an embedding and
    calls the collection's 'upsert' method with the right data.
    """
    # ARRANGE
    mock_gemini, mock_collection = mock_clients
    payload = {"report": "new data"}

    # ACT
    await report_cache.add("a new brief key", payload)

    # ASSERT
    mock_gemini.assert_called_once_with("a new brief key")
    mock_collection.upsert.assert_called_once()

    _, kwargs = mock_collection.upsert.call_args
    assert "ids" in kwargs
    assert "embeddings" in kwargs
    assert "documents" in kwargs

    assert kwargs["embeddings"][0] == [0.1, 0.2, 0.3]
    assert '{"report": "new data"}' in kwargs["documents"][0]
