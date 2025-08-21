"""
The Geolocation Utility: A Resilient, Multi-Provider Geolocation Service.

This module determines the user's geographical location based on their public IP
address. It is designed for high availability and performance by using multiple
API fallbacks and in-memory caching.
"""

import requests
import json
import time
from typing import Optional, Dict, Any

from .logger import get_logger

# Initialize a logger specific to this module
logger = get_logger(__name__)

# --- Configuration for Geolocation API Providers ---
# This list is prioritized. The system will try them in order.
GEOLOCATION_APIS = [
    {
        "name": "ip-api.com",
        "url": "http://ip-api.com/json",  # Use http for broader compatibility
        "parser": "_parse_ipapi_response",
    },
    {
        "name": "ipapi.co",
        "url": "https://ipapi.co/json/",
        "parser": "_parse_ipapico_response",
    },
]

# Simple in-memory cache to avoid repeated requests. TTL is in seconds.
_location_cache = {"location": None, "timestamp": 0, "ttl": 3600}  # 1 hour TTL


# --- Private Helper Functions ---


def _parse_ipapi_response(data: Dict[str, Any]) -> Optional[str]:
    """Parses the JSON response from ip-api.com."""
    if data.get("status") == "success":
        city = data.get("city")
        country = data.get("country")
        if city and country:
            return f"{city}, {country}"
    return None


def _parse_ipapico_response(data: Dict[str, Any]) -> Optional[str]:
    """Parses the JSON response from ipapi.co."""
    city = data.get("city")
    country_name = data.get("country_name")
    if city and country_name:
        return f"{city}, {country_name}"
    return None


def _is_cache_valid() -> bool:
    """Checks if the cached location is still valid."""
    if not _location_cache["location"]:
        return False
    elapsed = time.time() - _location_cache["timestamp"]
    return elapsed < _location_cache["ttl"]


def _cache_location(location: str):
    """Caches the location result with the current timestamp."""
    _location_cache["location"] = location
    _location_cache["timestamp"] = time.time()


def _try_geolocation_api(api_config: Dict[str, Any]) -> Optional[str]:
    """Attempts to get the location from a single geolocation API."""
    api_name = api_config["name"]
    logger.debug(f"Attempting geolocation lookup with {api_name}...")
    try:
        response = requests.get(api_config["url"], timeout=5)
        response.raise_for_status()
        data = response.json()

        parser_func_name = api_config["parser"]
        if parser_func_name == "_parse_ipapi_response":
            return _parse_ipapi_response(data)
        elif parser_func_name == "_parse_ipapico_response":
            return _parse_ipapico_response(data)

        return None
    except requests.exceptions.RequestException as e:
        logger.warning(
            f"Geolocation lookup with {api_name} failed due to a network error: {e}"
        )
        return None
    except json.JSONDecodeError:
        logger.warning(
            f"Geolocation lookup with {api_name} failed: Could not parse JSON response."
        )
        return None


# --- Public Function ---


def get_location_from_ip() -> Optional[str]:
    """
    Determines the user's location from their public IP with caching and fallbacks.
    This is the only function that should be called from outside this module.
    """
    logger.info("Attempting to determine user location from public IP...")

    # 1. Check cache first for performance
    if _is_cache_valid():
        cached_location = _location_cache["location"]
        logger.info(f"Using cached location: {cached_location}")
        return cached_location

    # 2. If cache is invalid, iterate through API providers
    for api_config in GEOLOCATION_APIS:
        location = _try_geolocation_api(api_config)
        if location:
            logger.info(
                f"Successfully determined location using {api_config['name']}: {location}"
            )
            _cache_location(location)
            return location

    # 3. If all providers fail
    logger.error("All geolocation APIs failed. Could not determine location.")
    return None
