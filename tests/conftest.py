# tests/conftest.py

import pytest
import json
import time
import requests
from pathlib import Path
from requests.exceptions import ConnectionError


@pytest.fixture(scope="session")
def expected_final_report():
    """Loads the expected final report from the fixture file."""
    fixture_path = Path(__file__).parent / "fixtures" / "expected_final_report.json"
    with open(fixture_path, "r") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def api_service_url():
    """The base URL for the API service, for use in E2E tests."""
    return "http://api:9500"
