# tests/catalyst/resilience/test_invoker.py

import json
import pytest
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional

from catalyst.clients import gemini
from catalyst.resilience.invoker import (
    _sanitize_ai_response,
    _normalize_lists_recursively,
    invoke_with_resilience,
)
from catalyst.resilience.exceptions import MaxRetriesExceededError

# --- Test Models for Validation ---


class SimpleItem(BaseModel):
    name: str
    value: int


class NestedModel(BaseModel):
    items: List[SimpleItem]
    tags: Optional[List[str]] = None
    metadata: Optional[dict] = None


class TopLevelModel(BaseModel):
    report_name: str
    nested_data: NestedModel


# --- Rigorous Unit Tests for Helper Functions ---


class TestSanitizationPipelineUnit:
    """Unit tests for the individual sanitization helper functions using pytest.mark.parametrize."""

    @pytest.mark.parametrize(
        "input_data, expected_output",
        [
            # Happy path: no change
            ({"key": ["value1", "value2"]}, {"key": ["value1", "value2"]}),
            # Basic stringified list
            ({"key": '["value1", "value2"]'}, {"key": ["value1", "value2"]}),
            # Basic stringified object
            ({"key": '{"subkey": "subvalue"}'}, {"key": {"subkey": "subvalue"}}),
            # Nested stringified list
            (
                {"data": [{"nested_key": '["a", "b"]'}]},
                {"data": [{"nested_key": ["a", "b"]}]},
            ),
            # Empty stringified list and object
            (
                {"empty_list": "[]", "empty_obj": "{}"},
                {"empty_list": [], "empty_obj": {}},
            ),
            # Invalid JSON string should be ignored
            ({"key": "[invalid json"}, {"key": "[invalid json"}),
            # Data with None should be preserved
            ({"key": None}, {"key": None}),
        ],
    )
    def test_sanitize_ai_response(self, input_data, expected_output):
        """Test _sanitize_ai_response with various edge cases."""
        assert _sanitize_ai_response(input_data) == expected_output

    @pytest.mark.parametrize(
        "input_data, expected_output",
        [
            # Basic case: wrap single item in list
            (
                {"items": {"name": "test", "value": 1}},
                {"items": [{"name": "test", "value": 1}]},
            ),
            # Basic case: wrap single string in list
            ({"items": [], "tags": "important"}, {"items": [], "tags": ["important"]}),
            # Should not change an already correct list
            (
                {"items": [{"name": "test", "value": 1}]},
                {"items": [{"name": "test", "value": 1}]},
            ),
            # Should not change an empty list
            ({"items": []}, {"items": []}),
            # Should handle None value correctly
            ({"items": [], "tags": None}, {"items": [], "tags": None}),
        ],
    )
    def test_normalize_lists_recursively(self, input_data, expected_output):
        """Test _normalize_lists_recursively with various edge cases."""
        assert _normalize_lists_recursively(input_data, NestedModel) == expected_output


# --- Realistic Integration Tests for the Main Invoker Function ---


@pytest.mark.asyncio
class TestInvokeWithResilienceIntegration:
    """
    More realistic integration tests for invoke_with_resilience.
    These tests mock the actual Google GenAI client to verify the integration.
    """

    async def test_happy_path_with_valid_data(self, mocker):
        """Test that a perfect response from the AI client passes through successfully."""
        valid_data = {
            "report_name": "Test Report",
            "nested_data": {
                "items": [{"name": "item1", "value": 100}],
                "tags": ["tag1"],
            },
        }
        response_text = json.dumps(valid_data)

        # Mock the actual Google GenAI client's response object structure
        mock_response = mocker.Mock()
        mock_response.text = response_text
        mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            return_value=mock_response,
        )

        result = await invoke_with_resilience(
            ai_function=gemini.generate_content_async,
            prompt="test prompt",
            response_schema=TopLevelModel,
        )
        assert isinstance(result, TopLevelModel)
        assert result.report_name == "Test Report"

    async def test_sanitization_path_fixes_common_ai_errors(self, mocker):
        """Test that a response with common AI errors is fixed by the sanitization pipeline."""
        dirty_data = {
            "report_name": "Dirty Report",
            "nested_data": {
                "items": {"name": "item1", "value": 100},  # Single item
                "tags": '["tag1", "tag2"]',  # Stringified list
            },
        }
        response_text = json.dumps(dirty_data)

        mock_response = mocker.Mock()
        mock_response.text = response_text
        mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            return_value=mock_response,
        )

        result = await invoke_with_resilience(
            ai_function=gemini.generate_content_async,
            prompt="test prompt",
            response_schema=TopLevelModel,
        )
        assert isinstance(result, TopLevelModel)
        assert result.report_name == "Dirty Report"
        assert isinstance(result.nested_data.items, list)
        assert result.nested_data.tags == ["tag1", "tag2"]

    async def test_failure_path_with_unrecoverable_error(self, mocker):
        """Test that an unfixable response (e.g., missing required field) raises an error."""
        invalid_data = {
            "report_name": "Invalid Report",
            "nested_data": {"tags": ["tag1"]},  # 'items' field is missing
        }
        response_text = json.dumps(invalid_data)

        mock_response = mocker.Mock()
        mock_response.text = response_text
        mocker.patch(
            "catalyst.clients.gemini.core.client.aio.models.generate_content",
            return_value=mock_response,
        )

        with pytest.raises(MaxRetriesExceededError) as exc_info:
            await invoke_with_resilience(
                ai_function=gemini.generate_content_async,
                prompt="test prompt",
                response_schema=TopLevelModel,
            )
        assert isinstance(exc_info.value.last_exception, ValidationError)
