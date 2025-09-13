# catalyst/clients/gemini/client_instance.py

"""
This module initializes and exports the single, shared instance of the
Google Gemini client.

This isolates the client object, preventing circular import issues between the
package's __init__.py (the public interface) and core.py (the implementation).
"""

from google import genai

from ... import settings
from ...utilities.logger import get_logger

logger = get_logger(__name__)

# Initialize the client to None to handle cases where the API key is missing.
client = None
try:
    if settings.GEMINI_API_KEY:
        # Updated client initialization for the Google GenAI SDK (2025)
        # The Client constructor only accepts these parameters:
        # - vertexai: bool (for Vertex AI API, defaults to False)
        # - api_key: str (for Gemini Developer API)
        # - credentials: google.auth.credentials.Credentials (for Vertex AI)
        # - project: str (for Vertex AI)
        # - location: str (for Vertex AI)
        # - debug_config: DebugConfig (for testing)
        # - http_options: HttpOptions (for API version, etc.)

        client = genai.Client(api_key=settings.GEMINI_API_KEY)
        logger.info("🔑 Gemini API client configured successfully.")
    else:
        logger.critical(
            "❌ GEMINI_API_KEY not found. The Gemini client will not function."
        )
except Exception as e:
    logger.critical(
        f"❌ CRITICAL: Failed to configure Gemini API client: {e}", exc_info=True
    )
