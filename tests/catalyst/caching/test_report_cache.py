# tests/catalyst/caching/test_report_cache.py

import pytest
import json
from unittest.mock import AsyncMock, MagicMock

# The module we are testing
from catalyst.caching import report_cache
from catalyst import settings


@pytest.fixture
def mock_chroma_collection(mocker) -> MagicMock:
    """A fixture to mock the ChromaDB collection object."""
    mock_collection = MagicMock()
    # We need to set the attribute on the module where it is used
    mocker.patch.object(report_cache, "_report_collection", mock_collection)
    return mock_collection


@pytest.fixture
def mock_gemini_embedding(mocker) -> AsyncMock:
    """A fixture to mock the Gemini embedding generation function."""
    # This is an async function, so we must use AsyncMock
    mock_embedding_func = mocker.patch(
        "catalyst.caching.report_cache.gemini.generate_embedding_async",
        new_callable=AsyncMock,
    )
    return mock_embedding_func


@pytest.mark.asyncio
class TestReportCacheCheck:
    """Comprehensive tests for the report_cache.check function."""

    async def test_check_cache_hit(self, mock_chroma_collection, mock_gemini_embedding):
        """Verify a successful cache hit when a close document is found."""
        # Arrange
        mock_gemini_embedding.return_value = [0.1, 0.2, 0.3]  # A mock vector

        # Simulate a ChromaDB query result for a close match
        mock_chroma_collection.query.return_value = {
            "documents": [["cached_payload_json_string"]],
            "distances": [
                [settings.CACHE_DISTANCE_THRESHOLD - 0.01]
            ],  # Below threshold
        }

        # Act
        result = await report_cache.check("test_key")

        # Assert
        assert result == "cached_payload_json_string"
        mock_gemini_embedding.assert_awaited_once_with("test_key")
        mock_chroma_collection.query.assert_called_once()

    async def test_check_cache_miss_distance_too_high(
        self, mock_chroma_collection, mock_gemini_embedding
    ):
        """Verify a cache miss when the closest document is outside the threshold."""
        # Arrange
        mock_gemini_embedding.return_value = [0.1, 0.2, 0.3]
        mock_chroma_collection.query.return_value = {
            "documents": [["some_document"]],
            "distances": [[settings.CACHE_DISTANCE_THRESHOLD + 0.1]],  # Above threshold
        }

        # Act
        result = await report_cache.check("test_key")

        # Assert
        assert result is None

    async def test_check_cache_miss_no_results(
        self, mock_chroma_collection, mock_gemini_embedding
    ):
        """Verify a cache miss when ChromaDB returns no documents."""
        # Arrange
        mock_gemini_embedding.return_value = [0.1, 0.2, 0.3]
        mock_chroma_collection.query.return_value = {
            "documents": [[]],
            "distances": [[]],
        }

        # Act
        result = await report_cache.check("test_key")

        # Assert
        assert result is None

    async def test_check_handles_embedding_failure(
        self, mock_chroma_collection, mock_gemini_embedding
    ):
        """Verify the function returns None if embedding generation fails."""
        # Arrange
        mock_gemini_embedding.return_value = None  # Simulate failure

        # Act
        result = await report_cache.check("test_key")

        # Assert
        assert result is None
        # The query should not have been called
        mock_chroma_collection.query.assert_not_called()

    async def test_check_handles_chromadb_failure(
        self, mock_chroma_collection, mock_gemini_embedding
    ):
        """Verify the function returns None if the ChromaDB query raises an exception."""
        # Arrange
        mock_gemini_embedding.return_value = [0.1, 0.2, 0.3]
        mock_chroma_collection.query.side_effect = Exception("Simulated DB error")

        # Act
        result = await report_cache.check("test_key")

        # Assert
        assert result is None


@pytest.mark.asyncio
class TestReportCacheAdd:
    """Comprehensive tests for the report_cache.add function."""

    async def test_add_success(self, mock_chroma_collection, mock_gemini_embedding):
        """Verify a successful add operation calls upsert with the correct data."""
        # Arrange
        brief_key = "my_semantic_key"
        payload = {"report": "final_report_data"}
        payload_json = json.dumps(payload)
        mock_embedding = [0.3, 0.2, 0.1]

        mock_gemini_embedding.return_value = mock_embedding

        # Act
        await report_cache.add(brief_key, payload)

        # Assert
        mock_gemini_embedding.assert_awaited_once_with(brief_key)

        # Check that upsert was called with the correct, structured arguments
        mock_chroma_collection.upsert.assert_called_once()
        call_args, call_kwargs = mock_chroma_collection.upsert.call_args

        assert isinstance(call_kwargs["ids"], list)
        assert isinstance(call_kwargs["ids"][0], str)  # ID should be a SHA256 hash
        assert call_kwargs["embeddings"] == [mock_embedding]
        assert call_kwargs["documents"] == [payload_json]
        assert call_kwargs["metadatas"] == [{"brief_key": brief_key}]

    async def test_add_handles_embedding_failure(
        self, mock_chroma_collection, mock_gemini_embedding
    ):
        """Verify that upsert is not called if embedding generation fails."""
        # Arrange
        mock_gemini_embedding.return_value = None  # Simulate failure

        # Act
        await report_cache.add("some_key", {"data": "payload"})

        # Assert
        # The most important assertion: the database was not written to.
        mock_chroma_collection.upsert.assert_not_called()
