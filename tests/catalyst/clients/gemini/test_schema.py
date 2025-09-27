# tests/catalyst/clients/gemini/test_schema.py

import pytest
from pydantic import BaseModel, Field

from catalyst.clients.gemini.schema import process_response_schema


# --- Test Models ---
class ValidModel(BaseModel):
    name: str


class IncompatibleModel(BaseModel):
    data: dict


class NestedIncompatibleModel(BaseModel):
    valid_field: str
    bad_field: IncompatibleModel


class TestGeminiSchemaProcessing:
    def test_process_response_schema_success(self):
        schema = process_response_schema(ValidModel)
        assert schema is not None
        assert "name" in schema["properties"]

    def test_process_response_schema_prunes_incompatible_model(self):
        schema = process_response_schema(IncompatibleModel)
        assert schema is None

    def test_process_response_schema_prunes_nested_incompatible_field(self):
        """
        The cleaner should now correctly identify that the 'bad_field' resolves to
        an invalid schema and prune it from the final properties.
        """
        schema = process_response_schema(NestedIncompatibleModel)
        assert schema is not None
        assert "valid_field" in schema["properties"]
        assert "bad_field" not in schema["properties"]

    def test_process_response_schema_handles_none(self):
        assert process_response_schema(None) is None
