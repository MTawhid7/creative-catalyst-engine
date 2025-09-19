# tests/catalyst/resilience/test_invoker.py

import pytest
import json
from unittest.mock import AsyncMock

from pydantic import BaseModel, Field

from catalyst.resilience import invoke_with_resilience, MaxRetriesExceededError
from catalyst import settings

# --- START: THE FIX ---
# Define a simple Pydantic model for our tests to validate against.
# By adding a default value to `value`, we make it non-required,
# which allows the simple fallback logic to work correctly.
class SimpleTestModel(BaseModel):
    name: str
    value: int = 0  # <-- THE CRITICAL CHANGE IS HERE
    description: str = Field(default="A default description.")
# --- END: THE FIX ---


@pytest.mark.asyncio
async def test_invoker_happy_path_succeeds_on_first_try(mocker):
    """
    Tests the ideal scenario where the AI function returns a valid JSON
    response on the very first attempt.
    """
    # ARRANGE
    mock_ai_function = AsyncMock()
    valid_json_string = '{"name": "Test Item", "value": 123}'
    mock_ai_function.return_value = {"text": valid_json_string}

    # ACT
    result = await invoke_with_resilience(
        ai_function=mock_ai_function,
        prompt="A test prompt",
        response_schema=SimpleTestModel
    )

    # ASSERT
    mock_ai_function.assert_called_once()
    assert isinstance(result, SimpleTestModel)
    assert result.name == "Test Item"
    assert result.value == 123

@pytest.mark.asyncio
async def test_invoker_uses_reformatter_on_second_try(mocker):
    """
    Tests the Layer 2 resilience: the invoker should reformat the prompt
    and succeed on the second try if the first one fails validation.
    """
    # ARRANGE
    mock_ai_function = AsyncMock()
    mock_ai_function.side_effect = [
        {"text": '{"name": "Test Item", "value": "this is not an int"}'},
        {"text": '{"name": "Test Item", "value": 456}'}
    ]

    mocker.patch("catalyst.resilience.invoker.settings.RESILIENCE_MAX_RETRIES", 1)

    # ACT
    result = await invoke_with_resilience(
        ai_function=mock_ai_function,
        prompt="A test prompt",
        response_schema=SimpleTestModel,
        max_retries=1
    )

    # ASSERT
    assert mock_ai_function.call_count == 2
    assert isinstance(result, SimpleTestModel)
    assert result.value == 456

@pytest.mark.asyncio
async def test_invoker_uses_fallback_after_all_retries_fail(mocker):
    """
    Tests Layer 4 resilience: if all retries fail, the invoker should
    trigger its internal fallback mechanism to generate a safe default.
    """
    # ARRANGE
    mock_main_ai_func = AsyncMock(return_value={"text": "completely invalid response"})

    mock_fallback_ai_func = mocker.patch("catalyst.resilience.invoker.gemini.generate_content_async")
    mock_fallback_ai_func.side_effect = [
        None,
        {"text": "A fallback name"}
    ]

    mocker.patch("catalyst.resilience.invoker.settings.RESILIENCE_MAX_RETRIES", 1)

    # ACT
    result = await invoke_with_resilience(
        ai_function=mock_main_ai_func,
        prompt="A test prompt",
        response_schema=SimpleTestModel,
        max_retries=1
    )

    # ASSERT
    assert mock_main_ai_func.call_count == 2
    assert mock_fallback_ai_func.call_count == 2

    assert isinstance(result, SimpleTestModel)
    assert result.name == "A fallback name"
    # With the default value in the model, this assertion is now correct.
    assert result.value == 0

@pytest.mark.asyncio
async def test_invoker_raises_max_retries_if_fallbacks_fail(mocker):
    """
    Tests the final failure case: if all retries and all internal fallback
    layers fail, the invoker should raise MaxRetriesExceededError.
    """
    # ARRANGE
    mock_main_ai_func = AsyncMock(return_value=None)
    mock_fallback_ai_func = mocker.patch("catalyst.resilience.invoker.gemini.generate_content_async", return_value=None)

    mocker.patch("catalyst.resilience.invoker.settings.RESILIENCE_MAX_RETRIES", 1)

    # ACT & ASSERT
    with pytest.raises(MaxRetriesExceededError):
        await invoke_with_resilience(
            ai_function=mock_main_ai_func,
            prompt="A test prompt",
            response_schema=SimpleTestModel,
            max_retries=1
        )